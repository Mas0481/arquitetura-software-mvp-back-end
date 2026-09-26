import asyncio
from datetime import date
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import Cliente, EmpresaEndereco, Endereco, Entrega
from app.routers import clientes, rotas
from app.schemas import GeocodeRequest
from app.services import external_maps as maps


class ExternalServicesTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        maps._geocode_cache.clear()
        maps._last_nominatim_request = 0
        maps._nominatim_lock = asyncio.Lock()
        self.real_client = httpx.AsyncClient

    def client(self, handler):
        return patch.object(maps.httpx, 'AsyncClient', side_effect=lambda **kwargs:
                            self.real_client(transport=httpx.MockTransport(handler), **kwargs))

    async def test_reverse_parameters_result_and_cache(self):
        requests = []
        def handler(request):
            requests.append(request)
            self.assertEqual(request.url.path, '/reverse')
            self.assertEqual(request.url.params['lat'], '-29.886')
            self.assertEqual(request.url.params['lon'], '-50.268')
            self.assertEqual(request.url.params['format'], 'jsonv2')
            self.assertIn('User-Agent', request.headers)
            return httpx.Response(200, json={'lat': '-29.88', 'lon': '-50.26',
                'display_name': 'Osório, RS', 'address': {'city': 'Osório'}})
        with self.client(handler):
            result = await maps.reverse_geocode(-29.886, -50.268)
            again = await maps.reverse_geocode(-29.886, -50.268)
        self.assertEqual(result, again)
        self.assertEqual(result['address']['city'], 'Osório')
        self.assertEqual(result['latitude'], -29.88)
        self.assertEqual(len(requests), 1)

    async def test_search_and_reverse_share_rate_limit(self):
        def handler(request):
            item = {'lat': '1', 'lon': '2', 'display_name': 'Teste'}
            return httpx.Response(200, json=[item] if request.url.path == '/search' else item)
        with self.client(handler), patch.object(maps.asyncio, 'sleep', new_callable=AsyncMock) as sleep:
            await maps.geocode_address(GeocodeRequest(logradouro='Rua A', cidade='Osório', estado='RS'))
            await maps.reverse_geocode(1, 2)
        sleep.assert_awaited_once()

    async def test_reverse_not_found_and_provider_failure(self):
        for status, body, expected in [(404, {}, 404), (200, {'error': 'Unable to geocode'}, 404), (503, {}, 502)]:
            maps._last_nominatim_request = 0
            with self.client(lambda request: httpx.Response(status, json=body)):
                with self.assertRaises(HTTPException) as caught:
                    await maps.reverse_geocode(1, 2)
                self.assertEqual(caught.exception.status_code, expected)

    async def test_malformed_json(self):
        with self.client(lambda request: httpx.Response(200, text='not json')):
            with self.assertRaises(HTTPException) as caught:
                await maps.reverse_geocode(1, 2)
            self.assertEqual(caught.exception.status_code, 502)

    async def test_matrix_coordinate_order_units_and_unreachable(self):
        def handler(request):
            self.assertEqual(request.url.path, '/table/v1/driving/2,1;4,3')
            self.assertEqual(request.url.params['annotations'], 'distance,duration')
            return httpx.Response(200, json={'code': 'Ok',
                'distances': [[0, 1250], [None, 0]], 'durations': [[0, 90], [None, 0]]})
        with self.client(handler):
            result = await maps.calculate_matrix([(1, 2), (3, 4)])
        self.assertEqual(result['distancias_km'], [[0, 1.25], [None, 0]])
        self.assertEqual(result['duracoes_minutos'], [[0, 1.5], [None, 0]])

    async def test_matrix_malformed_and_no_table(self):
        for body, status in [({'code': 'NoTable'}, 422),
                             ({'code': 'Ok', 'distances': [[0]], 'durations': [[0]]}, 502),
                             ({'code': 'Ok', 'distances': [[0, -1], [0, 0]], 'durations': [[0, 0], [0, 0]]}, 502)]:
            with self.client(lambda request: httpx.Response(200, json=body)):
                with self.assertRaises(HTTPException) as caught:
                    await maps.calculate_matrix([(1, 2), (3, 4)])
                self.assertEqual(caught.exception.status_code, status)

    async def test_matrix_timeout(self):
        def handler(request):
            raise httpx.ReadTimeout('timeout', request=request)
        with self.client(handler):
            with self.assertRaises(HTTPException) as caught:
                await maps.calculate_matrix([(1, 2), (3, 4)])
            self.assertEqual(caught.exception.status_code, 504)


class EndpointTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        self.session.add(EmpresaEndereco(id=1, logradouro='Empresa', cidade='Osório', estado='RS', latitude=1, longitude=2))
        for i in (1, 2):
            self.session.add(Cliente(id=i, nome=f'Cliente {i}'))
            self.session.add(Endereco(id=i, cliente_id=i, logradouro='Rua', cidade='Osório', estado='RS', latitude=i+2, longitude=i+3))
            self.session.add(Entrega(id=i, cliente_id=i, endereco_id=i, data_prevista=date.today()))
        self.session.commit()
        app = FastAPI()
        app.include_router(clientes.router)
        app.include_router(rotas.router)
        app.dependency_overrides[get_db] = lambda: self.session
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.session.close()
        self.engine.dispose()

    def test_reverse_rejects_invalid_coordinates(self):
        for body in [{'latitude': 91, 'longitude': 0}, {'latitude': 0, 'longitude': -181}, {'latitude': 0}]:
            self.assertEqual(self.client.post('/api/clientes/geocodificar-reverso', json=body).status_code, 422)

    def test_reverse_endpoint(self):
        result = {'latitude': 1, 'longitude': 2, 'display_name': 'Rua A', 'address': {}}
        with patch.object(clientes, 'reverse_geocode', new_callable=AsyncMock, return_value=result) as service:
            response = self.client.post('/api/clientes/geocodificar-reverso', json={'latitude': 1, 'longitude': 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), result)
        service.assert_awaited_once_with(1, 2)

    def test_matrix_preserves_delivery_order_and_company_first(self):
        result = {'distancias_km': [[0]*3 for _ in range(3)], 'duracoes_minutos': [[0]*3 for _ in range(3)]}
        with patch.object(rotas, 'calculate_matrix', new_callable=AsyncMock, return_value=result) as service:
            response = self.client.post('/api/rotas/matriz', json={'entrega_ids': [2, 1]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([p['entrega_id'] for p in response.json()['pontos']], [None, 2, 1])
        service.assert_awaited_once_with([(1, 2), (4, 5), (3, 4)])

    def test_matrix_missing_duplicate_and_limits(self):
        for ids, expected in [([], 422), (list(range(25)), 422), ([1, 1], 400), ([999], 404)]:
            self.assertEqual(self.client.post('/api/rotas/matriz', json={'entrega_ids': ids}).status_code, expected)

    def test_matrix_missing_coordinates(self):
        self.session.get(Endereco, 1).latitude = None
        self.session.commit()
        self.assertEqual(self.client.post('/api/rotas/matriz', json={'entrega_ids': [1]}).status_code, 400)

    def test_matrix_missing_company(self):
        self.session.delete(self.session.get(EmpresaEndereco, 1))
        self.session.commit()
        self.assertEqual(self.client.post('/api/rotas/matriz', json={'entrega_ids': [1]}).status_code, 400)

    def test_swagger_contains_both_new_endpoints(self):
        paths = self.client.get('/openapi.json').json()['paths']
        self.assertIn('/api/clientes/geocodificar-reverso', paths)
        self.assertIn('/api/rotas/matriz', paths)


if __name__ == '__main__':
    unittest.main()
