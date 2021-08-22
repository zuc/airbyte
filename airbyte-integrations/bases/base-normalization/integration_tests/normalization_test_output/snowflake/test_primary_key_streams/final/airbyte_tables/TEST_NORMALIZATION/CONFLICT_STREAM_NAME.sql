

      create or replace transient table AIRBYTE_DATABASE.TEST_NORMALIZATION.CONFLICT_STREAM_NAME  as
      (
-- Final base SQL model
select
    ID,
    CONFLICT_STREAM_NAME,
    _airbyte_emitted_at,
    _AIRBYTE_CONFLICT_STREAM_NAME_HASHID
from AIRBYTE_DATABASE._AIRBYTE_TEST_NORMALIZATION.CONFLICT_STREAM_NAME_AB3
-- CONFLICT_STREAM_NAME from "AIRBYTE_DATABASE".TEST_NORMALIZATION._AIRBYTE_RAW_CONFLICT_STREAM_NAME
      );
    