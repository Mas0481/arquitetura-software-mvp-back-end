CREATE DATABASE IF NOT EXISTS windroute
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE windroute;

CREATE TABLE IF NOT EXISTS clientes (
    id INT NOT NULL AUTO_INCREMENT,
    nome VARCHAR(150) NOT NULL,
    telefone VARCHAR(30),
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS enderecos (
    id INT NOT NULL AUTO_INCREMENT,
    cliente_id INT NOT NULL,
    logradouro VARCHAR(150) NOT NULL,
    numero VARCHAR(20),
    bairro VARCHAR(100),
    cidade VARCHAR(100) NOT NULL,
    estado VARCHAR(2) NOT NULL,
    cep VARCHAR(10),
    latitude DOUBLE,
    longitude DOUBLE,
    PRIMARY KEY (id),
    CONSTRAINT fk_endereco_cliente
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS empresa_endereco (
    id INT NOT NULL DEFAULT 1,
    logradouro VARCHAR(150) NOT NULL,
    numero VARCHAR(20),
    bairro VARCHAR(100),
    cidade VARCHAR(100) NOT NULL,
    estado VARCHAR(2) NOT NULL,
    cep VARCHAR(10),
    latitude DOUBLE,
    longitude DOUBLE,
    PRIMARY KEY (id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS entregas (
    id INT NOT NULL AUTO_INCREMENT,
    cliente_id INT NULL,
    endereco_id INT NULL,
    data_prevista DATE NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDENTE',
    observacoes TEXT,
    PRIMARY KEY (id),
    INDEX idx_entregas_data (data_prevista),
    INDEX idx_entregas_status (status),
    CONSTRAINT fk_entrega_cliente
        FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    CONSTRAINT fk_entrega_endereco
        FOREIGN KEY (endereco_id) REFERENCES enderecos(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS entregas_avulsas (
    entrega_id INT NOT NULL PRIMARY KEY,
    request_id VARCHAR(36) NOT NULL UNIQUE,
    nome VARCHAR(150) NOT NULL,
    endereco VARCHAR(500) NOT NULL,
    latitude DOUBLE NOT NULL,
    longitude DOUBLE NOT NULL,
    FOREIGN KEY (entrega_id) REFERENCES entregas(id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS rotas (
    id INT NOT NULL AUTO_INCREMENT,
    data_rota DATE NOT NULL,
    distancia_km DOUBLE NOT NULL DEFAULT 0,
    duracao_minutos INT NOT NULL DEFAULT 0,
    geometria_geojson LONGTEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'PLANEJADA',
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS rota_paradas (
    id INT NOT NULL AUTO_INCREMENT,
    rota_id INT NOT NULL,
    entrega_id INT NOT NULL,
    ordem INT NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uk_rota_ordem (rota_id, ordem),
    CONSTRAINT fk_rota_parada_rota
        FOREIGN KEY (rota_id) REFERENCES rotas(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_rota_parada_entrega
        FOREIGN KEY (entrega_id) REFERENCES entregas(id)
) ENGINE=InnoDB;
