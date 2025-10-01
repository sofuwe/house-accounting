from .models import Vendor, CampaignBDSIsrael



class MarketDataService:
    def get_vendor_to_bds_label_map(self) -> dict[int, str]:
        qs = Vendor.objects.values_list("id", "campaign_bds_israel__name")
        return {
            vendor_id: bds_label
            for vendor_id, bds_label in qs
        }
    
    def get_campaign_bds_israel_label_default(self) -> str:
        bds_default = (
            CampaignBDSIsrael.objects
            .filter(is_default=True)
            .values_list("name", flat=True)
            .first()
        )
        if bds_default is None:
            raise ValueError("No default BDS campaign found.")
        return bds_default
