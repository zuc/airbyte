{{ config(schema="TEST_NORMALIZATION", tags=["nested"]) }}
-- Final base SQL model
select
    {{ QUOTE('_AIRBYTE_CONFLICT_STREAM_NAME_HASHID') }},
    CONFLICT_STREAM_NAME,
    airbyte_emitted_at,
    {{ QUOTE('_AIRBYTE_CONFLICT_STREAM_NAME_2_HASHID') }}
from {{ ref('CONFLICT_STREAM_NAME_CONFLICT_STREAM_NAME_AB3') }}
-- CONFLICT_STREAM_NAME at conflict_stream_name/conflict_stream_name from {{ ref('CONFLICT_STREAM_NAME') }}

