
  create or replace  view AIRBYTE_DATABASE._AIRBYTE_TEST_NORMALIZATION.SIMPLE_STREAM_WITH_NAMESPACE_RESULTING_INTO_LONG_NAMES_AB2  as (
    
-- SQL model to cast each column to its adequate SQL type converted from the JSON schema type
select
    cast(ID as 
    varchar
) as ID,
    cast(DATE as 
    varchar
) as DATE,
    _airbyte_emitted_at
from AIRBYTE_DATABASE._AIRBYTE_TEST_NORMALIZATION.SIMPLE_STREAM_WITH_NAMESPACE_RESULTING_INTO_LONG_NAMES_AB1
-- SIMPLE_STREAM_WITH_NAMESPACE_RESULTING_INTO_LONG_NAMES
  );
