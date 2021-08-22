{{ config(schema="TEST_NORMALIZATION", tags=["top-level"]) }}
-- Final base SQL model
select
    ID,
    CONFLICT_STREAM_SCALAR,
    airbyte_emitted_at,
    {{ QUOTE('_AIRBYTE_CONFLICT_STREAM_SCALAR_HASHID') }}
from {{ ref('CONFLICT_STREAM_SCALAR_AB3') }}
-- CONFLICT_STREAM_SCALAR from {{ source('TEST_NORMALIZATION', 'AIRBYTE_RAW_CONFLICT_STREAM_SCALAR') }}

