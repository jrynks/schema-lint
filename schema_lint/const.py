"""Type families and default filter sets. Do not invent types that were not found."""

from __future__ import annotations

PRIMARY_TYPES = ("Course", "LocalBusiness", "FAQPage")
OPTIONAL_TYPES = ("Organization", "WebSite", "BreadcrumbList")
DEFAULT_TYPES = PRIMARY_TYPES

# Course family: CourseInstance is validated with Course rules when present.
COURSE_FAMILY = frozenset({"Course", "CourseInstance"})

# LocalBusiness + documented Schema.org subtypes commonly used by local clients.
# A page typed as Dentist / ProfessionalService / etc. is treated as this family.
LOCAL_BUSINESS_FAMILY = frozenset(
    {
        "LocalBusiness",
        "ProfessionalService",
        "MedicalBusiness",
        "Dentist",
        "Physician",
        "Pharmacy",
        "Hospital",
        "MedicalClinic",
        "PhysicianOffice",
        "VeterinaryCare",
        "Optician",
        "IndividualPhysician",
        "DiagnosticLab",
        "MedicalLaboratory",
        "CovidTestingFacility",
        "Restaurant",
        "CafeOrCoffeeShop",
        "BarOrPub",
        "Bakery",
        "FastFoodRestaurant",
        "IceCreamShop",
        "FoodEstablishment",
        "Brewery",
        "Winery",
        "Distillery",
        "Store",
        "ClothingStore",
        "ElectronicsStore",
        "FurnitureStore",
        "GroceryStore",
        "HardwareStore",
        "JewelryStore",
        "SportingGoodsStore",
        "AutoPartsStore",
        "BikeStore",
        "BookStore",
        "ConvenienceStore",
        "DepartmentStore",
        "Florist",
        "HobbyShop",
        "ShoeStore",
        "WholesaleStore",
        "GardenStore",
        "MobilePhoneStore",
        "ComputerStore",
        "OfficeEquipmentStore",
        "OutletStore",
        "PawnShop",
        "PetStore",
        "TireShop",
        "ToyStore",
        "LegalService",
        "Attorney",
        "Notary",
        "AccountingService",
        "AutomatedTeller",
        "FinancialService",
        "InsuranceAgency",
        "BankOrCreditUnion",
        "RealEstateAgent",
        "AutoRepair",
        "AutoDealer",
        "AutoBodyShop",
        "GasStation",
        "MotorcycleDealer",
        "AutoRental",
        "AutoWash",
        "MotorcycleRepair",
        "BeautySalon",
        "DaySpa",
        "HairSalon",
        "HealthClub",
        "NailSalon",
        "TattooParlor",
        "HealthAndBeautyBusiness",
        "LodgingBusiness",
        "Motel",
        "Hotel",
        "BedAndBreakfast",
        "Hostel",
        "Resort",
        "Campground",
        "Electrician",
        "GeneralContractor",
        "HVACBusiness",
        "HousePainter",
        "Locksmith",
        "MovingCompany",
        "Plumber",
        "RoofingContractor",
        "HomeAndConstructionBusiness",
        "SportsActivityLocation",
        "StadiumOrArena",
        "TennisComplex",
        "GolfCourse",
        "ExerciseGym",
        "BowlingAlley",
        "AutomotiveBusiness",
        "EntertainmentBusiness",
        "NightClub",
        "Casino",
        "ComedyClub",
        "MovieTheater",
        "AdultEntertainment",
        "TravelAgency",
        "TouristInformationCenter",
        "EmploymentAgency",
        "ChildCare",
        "Library",
        "InternetCafe",
        "EmergencyService",
        "FireStation",
        "PoliceStation",
        "GovernmentOffice",
        "PostOffice",
        "RecyclingCenter",
        "SelfStorage",
        "ShoppingCenter",
        "RadioStation",
        "TelevisionStation",
        "DryCleaningOrLaundry",
        "ArchiveOrganization",
        "AnimalShelter",
        "DentistOffice",
        "Optometric",
        "Podiatric",
        "MedicalTherapy",
        "Psychiatric",
        "Pharmacy",
    }
)

ORGANIZATION_FAMILY = frozenset(
    {"Organization", "NGO", "Corporation", "GovernmentOrganization", "EducationalOrganization", "SportsOrganization", "PerformingGroup", "NewsMediaOrganization"}
) | LOCAL_BUSINESS_FAMILY

SCHEMA_CONTEXT_MARKERS = (
    "schema.org",
    "www.schema.org",
)


def normalize_type(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    lowered = raw.lower()
    for prefix in (
        "https://schema.org/",
        "http://schema.org/",
        "https://www.schema.org/",
        "http://www.schema.org/",
        "schema:",
        "http://schema.org",
        "https://schema.org",
    ):
        if lowered.startswith(prefix):
            raw = raw[len(prefix) :].lstrip("/")
            break
    return raw.split("#")[-1].split("/")[-1]


def types_of(node: object) -> list[str]:
    if not isinstance(node, dict):
        return []
    raw = node.get("@type")
    if raw is None:
        return []
    values: list[str] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                n = normalize_type(item)
                if n:
                    values.append(n)
    elif isinstance(raw, str):
        n = normalize_type(raw)
        if n:
            values.append(n)
    # de-dupe, preserve order
    seen: set[str] = set()
    out: list[str] = []
    for t in values:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def family_for(requested: str) -> frozenset[str]:
    key = normalize_type(requested)
    if key in COURSE_FAMILY:
        return COURSE_FAMILY
    if key in LOCAL_BUSINESS_FAMILY:
        return LOCAL_BUSINESS_FAMILY
    if key == "FAQPage":
        return frozenset({"FAQPage"})
    if key in OPTIONAL_TYPES:
        if key == "Organization":
            # Organization filter should not swallow LocalBusiness (those have
            # their own, stricter rules). Only plain Organization-like types.
            return frozenset(ORGANIZATION_FAMILY - LOCAL_BUSINESS_FAMILY)
        return frozenset({key})
    return frozenset({key}) if key else frozenset()


def is_local_business(types: list[str]) -> bool:
    return any(t in LOCAL_BUSINESS_FAMILY for t in types)


def is_course_family(types: list[str]) -> bool:
    return any(t in COURSE_FAMILY for t in types)


def matches_requested(found_types: list[str], requested: list[str]) -> bool:
    if not requested:
        return True
    families = [family_for(r) for r in requested]
    return any(any(ft in fam for ft in found_types) for fam in families)
