-- Unity Catalog Setup
-- Configuração inicial do catálogo, schemas e permissões

-- Cria catálogo
CREATE CATALOG IF NOT EXISTS openrouter_catalog
COMMENT 'Catálogo principal do projeto OpenRouter Aula';

-- Usa o catálogo
USE CATALOG openrouter_catalog;

-- Cria schemas por camada
CREATE SCHEMA IF NOT EXISTS bronze
COMMENT 'Camada bronze - dados brutos ingeridos';

CREATE SCHEMA IF NOT EXISTS silver
COMMENT 'Camada silver - dados limpos e validados';

CREATE SCHEMA IF NOT EXISTS gold
COMMENT 'Camada gold - dados agregados e métricas de negócio';

CREATE SCHEMA IF NOT EXISTS sandbox
COMMENT 'Schema para experimentação e desenvolvimento';

-- Cria External Locations
CREATE EXTERNAL LOCATION IF NOT EXISTS `openrouter_catalog`.external_locations.`bronze_data`
URL 's3://openrouter-data-lake/bronze/'
WITH (STORAGE CREDENTIAL `aws_s3_credential`)
COMMENT 'Localização externa para dados bronze';

CREATE EXTERNAL LOCATION IF NOT EXISTS `openrouter_catalog`.external_locations.`silver_data`
URL 's3://openrouter-data-lake/silver/'
WITH (STORAGE CREDENTIAL `aws_s3_credential`)
COMMENT 'Localização externa para dados silver';

CREATE EXTERNAL LOCATION IF NOT EXISTS `openrouter_catalog`.external_locations.`gold_data`
URL 's3://openrouter-data-lake/gold/'
WITH (STORAGE CREDENTIAL `aws_s3_credential`)
COMMENT 'Localização externa para dados gold';

-- Cria Storage Credentials
-- CREATE STORAGE CREDENTIAL aws_s3_credential
-- WITH (AWS_IAM_ROLE = 'arn:aws:iam::123456789:role/databricks-s3-access');

-- Cria grupos e usuários
-- CREATE GROUP IF NOT EXISTS data_engineers;
-- CREATE GROUP IF NOT EXISTS data_analysts;
-- CREATE GROUP IF NOT EXISTS data_scientists;

-- Concede permissões
GRANT ALL PRIVILEGES ON CATALOG openrouter_catalog TO `data_engineers`;
GRANT USE CATALOG ON CATALOG openrouter_catalog TO `data_analysts`;
GRANT USE SCHEMA, READ VOLUME ON SCHEMA openrouter_catalog.gold TO `data_analysts`;
GRANT USE SCHEMA, READ VOLUME ON SCHEMA openrouter_catalog.silver TO `data_analysts`;

-- Cria tags padrão
-- ALTER CATALOG openrouter_catalog SET TAGS ('environment' = 'production', 'team' = 'data-engineering');

-- Cria volumes para dados não-tabulares
CREATE VOLUME IF NOT EXISTS bronze.raw_files
COMMENT 'Volume para arquivos brutos não estruturados';

CREATE VOLUME IF NOT EXISTS silver.processed_files
COMMENT 'Volume para arquivos processados';

CREATE VOLUME IF NOT EXISTS gold.reports
COMMENT 'Volume para relatórios e exports';

-- Comentário final
COMMENT ON CATALOG openrouter_catalog IS
'Catálogo OpenRouter Aula - Arquitetura Medalhão (Bronze/Silver/Gold) com Unity Catalog';