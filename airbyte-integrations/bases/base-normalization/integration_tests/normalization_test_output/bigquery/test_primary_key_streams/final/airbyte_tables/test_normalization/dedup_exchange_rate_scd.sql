

  create or replace table dataline-integration-testing.test_normalization.dedup_exchange_rate_scd
  
  
  OPTIONS()
  as (
    
-- SQL model to build a Type 2 Slowly Changing Dimension (SCD) table for each record identified by their primary key
select
    id,
    currency,
    date,
    timestamp_col,
    HKD_special___characters,
    HKD_special___characters_1,
    NZD,
    USD,
    date as _airbyte_start_at,
    lag(date) over (
        partition by id, currency, cast(NZD as 
    string
)
        order by date is null asc, date desc, _airbyte_emitted_at desc
    ) as _airbyte_end_at,
    lag(date) over (
        partition by id, currency, cast(NZD as 
    string
)
        order by date is null asc, date desc, _airbyte_emitted_at desc
    ) is null as _airbyte_active_row,
    _airbyte_emitted_at,
    _airbyte_dedup_exchange_rate_hashid
from dataline-integration-testing._airbyte_test_normalization.dedup_exchange_rate_ab4
-- dedup_exchange_rate from `dataline-integration-testing`.test_normalization._airbyte_raw_dedup_exchange_rate
where _airbyte_row_num = 1
  );
    