import json
import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects import mysql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.schema import CreateTable

from app.database import Base, get_db
from app.models import EmpresaEndereco, Cliente, Endereco, Entrega, Rota, RotaParada
from app.routers import rotas
from app.services import external_maps as maps


class RoutingProviderTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client_class = httpx.AsyncClient

    def provider(self, handler):
        return patch.object(maps.httpx, 'AsyncClient', side_effect=lambda **kwargs:
            self.client_class(transport=httpx.MockTransport(handler), **kwargs))

    async def test_codes_are_read_from_error_http_responses(self):
        for code in ['NoRoute', 'NoSegment', 'TooBig', 'InvalidValue']:
            with self.subTest(code=code), self.provider(lambda request: httpx.Response(400, json={'code':code, 'message':'private provider details'})):
                with self.assertRaises(HTTPException) as error:
                    await maps.calculate_route([(1,2),(3,4)])
                self.assertEqual(error.exception.status_code, 422)
                self.assertEqual(error.exception.detail['codigo'], code)
                self.assertTrue(error.exception.detail['orientacao'])
                self.assertNotIn('private provider details', str(error.exception.detail))

    async def test_timeout_and_connection(self):
        for failure,status,code in [(httpx.ReadTimeout,504,'Timeout'),(httpx.ConnectError,503,'ConnectionError')]:
            def handler(request): raise failure('technical details',request=request)
            with self.provider(handler), self.assertRaises(HTTPException) as error:
                await maps.calculate_route([(1,2),(3,4)])
            self.assertEqual(error.exception.status_code,status)
            self.assertEqual(error.exception.detail['codigo'],code)

    async def test_rate_limit_and_unavailable(self):
        for status,code in [(429,'RateLimited'),(503,'Unavailable')]:
            with self.provider(lambda request: httpx.Response(status, text='server error')), self.assertRaises(HTTPException) as error:
                await maps.calculate_route([(1,2),(3,4)])
            self.assertEqual(error.exception.status_code,503)
            self.assertEqual(error.exception.detail['codigo'],code)

    async def test_invalid_payloads(self):
        for payload in [[],{}, {'code':'Ok','routes':[]}, {'code':'Ok','routes':[{'distance':1,'duration':2,'geometry':None}]}, {'code':'SomethingElse'}]:
            with self.provider(lambda request: httpx.Response(200,json=payload)), self.assertRaises(HTTPException) as error:
                await maps.calculate_route([(1,2),(3,4)])
            self.assertEqual(error.exception.status_code,502)
        with self.provider(lambda request: httpx.Response(200,text='<html>bad gateway</html>')), self.assertRaises(HTTPException) as error:
            await maps.calculate_route([(1,2),(3,4)])
        self.assertEqual(error.exception.detail['codigo'],'InvalidResponse')

    async def test_invalid_coordinates_do_not_call_provider(self):
        with patch.object(maps.httpx,'AsyncClient') as client, self.assertRaises(HTTPException) as error:
            await maps.calculate_route([(91,2),(3,4)])
        client.assert_not_called()
        self.assertEqual(error.exception.detail['codigo'],'InvalidCoordinates')

    async def test_large_geometry_keeps_all_points(self):
        points=[[-50+i/100000, -29+i/100000] for i in range(6000)]
        geometry={'type':'LineString','coordinates':points}
        self.assertGreater(len(json.dumps(geometry).encode()),65535)
        def handler(request):
            self.assertEqual(request.url.path,'/route/v1/driving/2,1;4,3')
            return httpx.Response(200,json={'code':'Ok','routes':[{'distance':608990,'duration':31140,'geometry':geometry}]})
        with self.provider(handler): result=await maps.calculate_route([(1,2),(3,4)])
        self.assertEqual(result['geometry'],geometry)
        self.assertEqual(result['distance_km'],608.99)
        self.assertEqual(result['duration_minutes'],519)


class RoutingPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db=sessionmaker(bind=self.engine)()
        self.db.add(EmpresaEndereco(id=1,logradouro='Empresa',cidade='Teste',estado='RS',latitude=1,longitude=2))
        customer=Cliente(nome='Teste')
        customer.enderecos.append(Endereco(logradouro='Rua',cidade='Teste',estado='RS',latitude=3,longitude=4))
        self.db.add(customer);self.db.flush()
        delivery=Entrega(cliente_id=customer.id,endereco_id=customer.enderecos[0].id,data_prevista=date.today())
        self.db.add(delivery);self.db.commit();self.delivery_id=delivery.id
        app=FastAPI();app.include_router(rotas.router);app.dependency_overrides[get_db]=lambda:self.db
        self.client=TestClient(app)
        self.result={'distance_km':1,'duration_minutes':2,'geometry':{'type':'LineString','coordinates':[[2,1],[4,3]]}}

    def tearDown(self):
        self.client.close();self.db.close();self.engine.dispose()

    def test_mysql_model_uses_longtext(self):
        self.assertIn('geometria_geojson LONGTEXT',str(CreateTable(Rota.__table__).compile(dialect=mysql.dialect())))

    def test_commit_failure_rolls_back_and_returns_clear_error(self):
        with patch.object(rotas,'calculate_route',new_callable=AsyncMock,return_value=self.result), patch.object(self.db,'commit',side_effect=SQLAlchemyError('database details')):
            response=self.client.post('/api/rotas/calcular',json={'entrega_ids':[self.delivery_id]})
        self.assertEqual(response.status_code,500)
        self.assertEqual(response.json()['detail']['codigo'],'PersistenceError')
        self.assertNotIn('database details',response.text)
        self.assertEqual(self.db.query(Rota).count(),0)
        self.assertEqual(self.db.query(RotaParada).count(),0)

    def test_provider_error_does_not_save_route(self):
        with patch.object(rotas,'calculate_route',new_callable=AsyncMock,side_effect=maps.routing_error(422,'NoRoute','Sem trajeto','Confira os pontos')):
            response=self.client.post('/api/rotas/calcular',json={'entrega_ids':[self.delivery_id]})
        self.assertEqual(response.status_code,422)
        self.assertEqual(self.db.query(Rota).count(),0)

    def test_large_route_is_saved_without_truncation(self):
        geometry={'type':'LineString','coordinates':[[2+i/100000,1+i/100000] for i in range(6000)]}
        with patch.object(rotas,'calculate_route',new_callable=AsyncMock,return_value={**self.result,'geometry':geometry}):
            response=self.client.post('/api/rotas/calcular',json={'entrega_ids':[self.delivery_id]})
        self.assertEqual(response.status_code,200,response.text)
        stored=self.db.query(Rota).one()
        self.assertEqual(json.loads(stored.geometria_geojson),geometry)

    def test_swagger_has_error_contract(self):
        schema=self.client.get('/openapi.json').json()
        responses=schema['paths']['/api/rotas/calcular']['post']['responses']
        for status in ['422','500','502','503','504']: self.assertIn(status,responses)
