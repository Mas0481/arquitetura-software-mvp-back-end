from datetime import date
from uuid import uuid4
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import Cliente, Endereco, Entrega, EntregaAvulsa, EmpresaEndereco, Rota, RotaParada
from app.routers import entregas, rotas


class AvulsaTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        app = FastAPI()
        app.include_router(entregas.router)
        app.include_router(rotas.router)
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)
        self.body = {'nome': 'Avulsa SP', 'endereco': 'Avenida Paulista, São Paulo',
                     'latitude': -23.5614, 'longitude': -46.6559,
                     'data_prevista': date.today().isoformat(), 'observacoes': 'Recepção',
                     'request_id': str(uuid4())}

    def tearDown(self):
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def create(self):
        response = self.client.post('/api/entregas/avulsas', json=self.body)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_create_list_and_exact_coordinates_without_customer(self):
        data = self.create()
        self.assertTrue(data['avulsa'])
        self.assertIsNone(data['cliente_id'])
        self.assertIsNone(data['endereco_id'])
        self.assertEqual(data['latitude'], self.body['latitude'])
        self.assertEqual(data['longitude'], self.body['longitude'])
        self.assertEqual(self.db.query(Cliente).count(), 0)
        self.assertEqual(self.db.query(Endereco).count(), 0)
        self.assertEqual(self.client.get('/api/entregas').json()[0], data)

    def test_retry_does_not_duplicate(self):
        first = self.create()
        second = self.create()
        self.assertEqual(first['id'], second['id'])
        self.assertEqual(self.db.query(Entrega).count(), 1)
        self.assertEqual(self.db.query(EntregaAvulsa).count(), 1)

    def test_retry_with_other_data_conflicts(self):
        self.create()
        self.body['nome'] = 'Outra pessoa'
        self.assertEqual(self.client.post('/api/entregas/avulsas', json=self.body).status_code, 409)

    def test_validation(self):
        for change in [{'latitude':91}, {'longitude':181}, {'endereco':'   '}, {'nome':' '}, {'request_id':'invalid'}, {'data_prevista':'invalid'}]:
            response = self.client.post('/api/entregas/avulsas', json={**self.body, **change})
            self.assertEqual(response.status_code, 422)
        self.assertEqual(self.db.query(Entrega).count(), 0)

    def test_edit_and_delete(self):
        data = self.create()
        updated = {**self.body, 'nome':'Avulsa editada', 'longitude':-46.66}
        response = self.client.put(f"/api/entregas/avulsas/{data['id']}", json=updated)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['cliente_nome'], 'Avulsa editada')
        self.assertEqual(response.json()['longitude'], -46.66)
        self.assertEqual(self.client.delete(f"/api/entregas/{data['id']}").status_code, 204)
        self.assertEqual(self.db.query(EntregaAvulsa).count(), 0)
        self.assertEqual(self.db.query(Entrega).count(), 0)

    def add_company(self):
        self.db.add(EmpresaEndereco(id=1, logradouro='Empresa', cidade='São Paulo', estado='SP', latitude=-23.55, longitude=-46.64))
        self.db.commit()

    def test_matrix_accepts_avulsa(self):
        data = self.create()
        self.add_company()
        response_matrix = {'distancias_km': [[0,1],[1,0]], 'duracoes_minutos': [[0,2],[2,0]]}
        with patch.object(rotas, 'calculate_matrix', new_callable=AsyncMock, return_value=response_matrix) as service:
            response = self.client.post('/api/rotas/matriz', json={'entrega_ids':[data['id']]})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['pontos'][1]['nome'], 'Avulsa SP')
        service.assert_awaited_once_with([(-23.55,-46.64),(-23.5614,-46.6559)])

    def test_route_and_invalidation_on_edit(self):
        data = self.create()
        self.add_company()
        route = {'distance_km':1, 'duration_minutes':2, 'geometry':{'type':'LineString', 'coordinates':[]}}
        with patch.object(rotas, 'calculate_route', new_callable=AsyncMock, return_value=route):
            response = self.client.post('/api/rotas/calcular', json={'entrega_ids':[data['id']]})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['paradas'][0]['cliente_nome'], 'Avulsa SP')
        self.assertEqual(self.db.query(Rota).count(), 1)
        response = self.client.put(f"/api/entregas/avulsas/{data['id']}", json={**self.body, 'nome':'Atualizada'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.db.query(Rota).count(), 0)
        self.assertEqual(self.db.query(RotaParada).count(), 0)

    def test_delete_cascades_route(self):
        data = self.create()
        self.add_company()
        route = {'distance_km':1, 'duration_minutes':2, 'geometry':{}}
        with patch.object(rotas, 'calculate_route', new_callable=AsyncMock, return_value=route):
            self.client.post('/api/rotas/calcular', json={'entrega_ids':[data['id']]})
        self.assertEqual(self.client.delete(f"/api/entregas/{data['id']}").status_code, 204)
        self.assertEqual(self.db.query(Rota).count(), 0)
        self.assertEqual(self.db.query(EntregaAvulsa).count(), 0)

    def test_regular_deliveries_still_work(self):
        customer = Cliente(nome='Cliente existente')
        customer.enderecos.append(Endereco(logradouro='Rua', cidade='Osório', estado='RS', latitude=-29.8, longitude=-50.2))
        self.db.add(customer); self.db.commit()
        response = self.client.post('/api/entregas', json={'cliente_id':customer.id,'endereco_id':customer.enderecos[0].id,'data_prevista':date.today().isoformat()})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertFalse(response.json()['avulsa'])
        delivery_id = response.json()['id']
        self.assertEqual(self.client.put(f'/api/entregas/avulsas/{delivery_id}', json=self.body).status_code, 404)

    def test_swagger_documents_nullable_ids_and_new_routes(self):
        schema = self.client.get('/openapi.json').json()
        self.assertIn('/api/entregas/avulsas', schema['paths'])
        self.assertIn('/api/entregas/avulsas/{entrega_id}', schema['paths'])
        self.assertIn('request_id', schema['components']['schemas']['EntregaAvulsaCreate']['properties'])
        self.assertIn({'type':'null'}, schema['components']['schemas']['EntregaOut']['properties']['cliente_id']['anyOf'])
