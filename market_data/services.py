from .models import Vendor


class MarketDataReadService:
    def get_vendor_id_map(self) -> dict[str, int]:
        return dict(Vendor.objects.all().values_list("natural_id", "id"))


class MarketDataWriteService:
    def bulk_create_or_update_vendors(self, vendors: list[tuple[str, str]]) -> tuple[int, int]:
        vendors_existing: set[str] = set(Vendor.objects.values_list("natural_id", flat=True))

        vendors_to_create: list[Vendor] = []
        for vendor_id, vendor_name in vendors:
            if vendor_id in vendors_existing:
                continue
            vendors_to_create.append(
                Vendor(natural_id=vendor_id, name=vendor_id),
            )
            vendors_existing.add(vendor_id)

        Vendor.objects.bulk_create(vendors_to_create)

        return len(vendors_to_create), 0
