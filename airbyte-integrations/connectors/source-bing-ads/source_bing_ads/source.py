#
# MIT License
#
# Copyright (c) 2020 Airbyte
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#


from abc import ABC, abstractmethod
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple

from airbyte_cdk import AirbyteLogger
from airbyte_cdk.models import SyncMode
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from source_bing_ads.cache import VcrCache
from source_bing_ads.client import Client
from suds import sudsobject

CACHE: VcrCache = VcrCache()


class BingAdsStream(Stream, ABC):
    primary_key: str = "Id"
    # indicates whether stream should cache incoming responses via VcrCache
    use_cache: bool = False

    def __init__(self, client: Client, config: Mapping[str, Any]) -> None:
        super().__init__()
        self.client = client
        self.config = config

    @property
    @abstractmethod
    def data_field(self) -> str:
        """
        Specifies root object name in a stream response
        """
        pass

    @property
    @abstractmethod
    def service_name(self) -> str:
        """
        Specifies bing ads service name for a current stream
        """
        pass

    @property
    @abstractmethod
    def operation_name(self) -> str:
        """
        Specifies operation name to use for a current stream
        """
        pass

    @property
    @abstractmethod
    def additional_fields(self) -> Optional[str]:
        """
        Specifies which additional fields to fetch for a current stream.
        Expected format: field names separated by space
        """
        pass

    def next_page_token(self, response: sudsobject.Object, **kwargs: Mapping[str, Any]) -> Optional[Mapping[str, Any]]:
        """
        Default method for streams that don't support pagination
        """
        return None

    def parse_response(self, response: sudsobject.Object, **kwargs) -> Iterable[Mapping]:
        if response is not None and hasattr(response, self.data_field):
            yield from self.client.asdict(response)[self.data_field]

        yield from []

    def send_request(self, params: Mapping[str, Any], account_id: str = None) -> Mapping[str, Any]:
        request_kwargs = {
            "service_name": self.service_name,
            "account_id": account_id,
            "operation_name": self.operation_name,
            "params": params,
        }
        if not self.use_cache:
            return self.client.request(**request_kwargs)

        with CACHE.use_cassette():
            return self.client.request(**request_kwargs)

    def get_account_id(self, stream_slice: Mapping[str, Any] = None) -> Optional[str]:
        """
        Fetches account_id from slice object
        """
        return stream_slice.get("account_id") if stream_slice else None

    def read_records(
        self,
        sync_mode: SyncMode,
        stream_slice: Mapping[str, Any] = None,
        stream_state: Mapping[str, Any] = None,
        **kwargs: Mapping[str, Any],
    ) -> Iterable[Mapping[str, Any]]:
        stream_state = stream_state or {}
        next_page_token = None

        while True:
            params = self.request_params(
                stream_state=stream_state,
                stream_slice=stream_slice,
                next_page_token=next_page_token,
            )

            response = self.send_request(params, account_id=self.get_account_id(stream_slice))
            for record in self.parse_response(response):
                yield record

            next_page_token = self.next_page_token(response, current_page_token=next_page_token)
            if not next_page_token:
                break

        yield from []


class Accounts(BingAdsStream):
    """
    Searches for accounts that the current authenticated user can access.
    API doc: https://docs.microsoft.com/en-us/advertising/customer-management-service/searchaccounts?view=bingads-13
    Account schema: https://docs.microsoft.com/en-us/advertising/customer-management-service/advertiseraccount?view=bingads-13
    Stream caches incoming responses to be able to reuse this data in Campaigns stream
    """

    use_cache: bool = True
    data_field: str = "AdvertiserAccount"
    service_name: str = "CustomerManagementService"
    operation_name: str = "SearchAccounts"
    additional_fields: str = "TaxCertificate AccountMode"
    # maximum page size
    page_size_limit: int = 1000

    def next_page_token(self, response: sudsobject.Object, current_page_token: Optional[int]) -> Optional[Mapping[str, Any]]:
        current_page_token = current_page_token or 0
        if response is not None and hasattr(response, self.data_field):
            return None if self.page_size_limit > len(response[self.data_field]) else current_page_token + 1
        else:
            return None

    def request_params(
        self,
        next_page_token: Mapping[str, Any] = None,
        **kwargs: Mapping[str, Any],
    ) -> MutableMapping[str, Any]:
        predicates = {
            "Predicate": [
                {
                    "Field": "UserId",
                    "Operator": "Equals",
                    "Value": self.config["user_id"],
                }
            ]
        }

        if self.config["accounts"]["selection_strategy"] == "subset":
            predicates["Predicate"].append(
                {
                    "Field": "AccountId",
                    "Operator": "In",
                    "Value": ",".join(self.config["accounts"]["ids"]),
                }
            )

        paging = self.client.get_service(service_name=self.service_name).factory.create("ns5:Paging")
        paging.Index = next_page_token or 0
        paging.Size = self.page_size_limit
        return {
            "PageInfo": paging,
            "Predicates": predicates,
            "ReturnAdditionalFields": self.additional_fields,
        }


class Campaigns(BingAdsStream):
    """
    Gets the campaigns for all provided accounts.
    API doc: https://docs.microsoft.com/en-us/advertising/campaign-management-service/getcampaignsbyaccountid?view=bingads-13
    Campaign schema: https://docs.microsoft.com/en-us/advertising/campaign-management-service/campaign?view=bingads-13
    Stream caches incoming responses to be able to reuse this data in AdGroups stream
    """

    # Stream caches incoming responses to avoid duplicated http requests
    use_cache: bool = True
    data_field: str = "Campaign"
    service_name: str = "CampaignManagement"
    operation_name: str = "GetCampaignsByAccountId"
    additional_fields: str = (
        "AdScheduleUseSearcherTimeZone BidStrategyId CpvCpmBiddingScheme DynamicDescriptionSetting"
        " DynamicFeedSetting MaxConversionValueBiddingScheme MultimediaAdsBidAdjustment"
        " TargetImpressionShareBiddingScheme TargetSetting VerifiedTrackingSetting"
    )

    def request_params(
        self,
        stream_slice: Mapping[str, Any] = None,
        **kwargs: Mapping[str, Any],
    ) -> MutableMapping[str, Any]:
        return {
            "AccountId": stream_slice["account_id"],
            "ReturnAdditionalFields": self.additional_fields,
        }

    def stream_slices(
        self,
        **kwargs: Mapping[str, Any],
    ) -> Iterable[Optional[Mapping[str, Any]]]:
        for account in Accounts(self.client, self.config).read_records(SyncMode.full_refresh):
            yield {"account_id": account["Id"]}

        yield from []


class AdGroups(BingAdsStream):
    """
    Gets the ad groups for all provided accounts.
    API doc: https://docs.microsoft.com/en-us/advertising/campaign-management-service/getadgroupsbycampaignid?view=bingads-13
    AdGroup schema: https://docs.microsoft.com/en-us/advertising/campaign-management-service/adgroup?view=bingads-13
    Stream caches incoming responses to be able to reuse this data in Ads stream
    """

    # Stream caches incoming responses to avoid duplicated http requests
    use_cache: bool = True
    data_field: str = "AdGroup"
    service_name: str = "CampaignManagement"
    operation_name: str = "GetAdGroupsByCampaignId"
    additional_fields: str = "AdGroupType AdScheduleUseSearcherTimeZone CpmBid CpvBid MultimediaAdsBidAdjustment"

    def request_params(
        self,
        stream_slice: Mapping[str, Any] = None,
        **kwargs: Mapping[str, Any],
    ) -> MutableMapping[str, Any]:
        return {"CampaignId": stream_slice["campaign_id"], "ReturnAdditionalFields": self.additional_fields}

    def stream_slices(
        self,
        **kwargs: Mapping[str, Any],
    ) -> Iterable[Optional[Mapping[str, Any]]]:
        campaigns = Campaigns(self.client, self.config)
        for account in Accounts(self.client, self.config).read_records(SyncMode.full_refresh):
            for campaign in campaigns.read_records(sync_mode=SyncMode.full_refresh, stream_slice={"account_id": account["Id"]}):
                yield {"campaign_id": campaign["Id"], "account_id": account["Id"]}

        yield from []


class Ads(BingAdsStream):
    """
    Retrieves the ads for all provided accounts.
    API doc: https://docs.microsoft.com/en-us/advertising/campaign-management-service/getadsbyadgroupid?view=bingads-13
    Ad schema: https://docs.microsoft.com/en-us/advertising/campaign-management-service/ad?view=bingads-13
    """

    data_field: str = "Ad"
    service_name: str = "CampaignManagement"
    operation_name: str = "GetAdsByAdGroupId"
    additional_fields: str = "ImpressionTrackingUrls Videos LongHeadlines"
    ad_types: Iterable[str] = [
        "Text",
        "Image",
        "Product",
        "AppInstall",
        "ExpandedText",
        "DynamicSearch",
        "ResponsiveAd",
        "ResponsiveSearch",
    ]

    def request_params(
        self,
        stream_slice: Mapping[str, Any] = None,
        **kwargs: Mapping[str, Any],
    ) -> MutableMapping[str, Any]:
        return {
            "AdGroupId": stream_slice["ad_group_id"],
            "AdTypes": {"AdType": self.ad_types},
            "ReturnAdditionalFields": self.additional_fields,
        }

    def stream_slices(
        self,
        **kwargs: Mapping[str, Any],
    ) -> Iterable[Optional[Mapping[str, Any]]]:
        ad_groups = AdGroups(self.client, self.config)
        for slice in ad_groups.stream_slices(sync_mode=SyncMode.full_refresh):
            for ad_group in ad_groups.read_records(sync_mode=SyncMode.full_refresh, stream_slice=slice):
                yield {"ad_group_id": ad_group["Id"], "account_id": slice["account_id"]}
        yield from []


class SourceBingAds(AbstractSource):
    """
    Source implementation of Bing Ads API. Fetches advertising data from accounts
    """

    def check_connection(self, logger: AirbyteLogger, config: Mapping[str, Any]) -> Tuple[bool, Any]:
        try:
            client = Client(**config)
            account_ids = {str(account["Id"]) for account in Accounts(client, config).read_records(SyncMode.full_refresh)}

            if config["accounts"]["selection_strategy"] == "subset":
                config_account_ids = set(config["accounts"]["ids"])
                if not config_account_ids.issubset(account_ids):
                    raise Exception(f"Accounts with ids: {config_account_ids.difference(account_ids)} not found on this user.")
            elif config["accounts"]["selection_strategy"] == "all":
                if not account_ids:
                    raise Exception("You don't have accounts assigned to this user.")
            else:
                raise Exception("Incorrect account selection strategy.")
        except Exception as error:
            return False, error

        return True, None

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        client = Client(**config)
        return [
            Accounts(client, config),
            AdGroups(client, config),
            Ads(client, config),
            Campaigns(client, config),
        ]
