export const COURSE_FAMILY = new Set(["Course", "CourseInstance"]);

export const LOCAL_BUSINESS_FAMILY = new Set([
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
]);

const ORG_EXTRA = new Set([
  "Organization",
  "NGO",
  "Corporation",
  "GovernmentOrganization",
  "EducationalOrganization",
  "SportsOrganization",
  "PerformingGroup",
  "NewsMediaOrganization",
]);

export const ORGANIZATION_FAMILY = new Set([...ORG_EXTRA, ...LOCAL_BUSINESS_FAMILY]);

export function normalizeType(value: string): string {
  let raw = (value || "").trim();
  if (!raw) return "";
  const lowered = raw.toLowerCase();
  const prefixes = [
    "https://schema.org/",
    "http://schema.org/",
    "https://www.schema.org/",
    "http://www.schema.org/",
    "schema:",
  ];
  for (const prefix of prefixes) {
    if (lowered.startsWith(prefix)) {
      raw = raw.slice(prefix.length).replace(/^\//, "");
      break;
    }
  }
  const hash = raw.split("#");
  raw = hash[hash.length - 1] ?? raw;
  const slash = raw.split("/");
  return slash[slash.length - 1] ?? raw;
}

export function typesOf(node: unknown): string[] {
  if (!node || typeof node !== "object" || Array.isArray(node)) return [];
  const raw = (node as Record<string, unknown>)["@type"];
  const values: string[] = [];
  if (Array.isArray(raw)) {
    for (const item of raw) {
      if (typeof item === "string") {
        const n = normalizeType(item);
        if (n) values.push(n);
      }
    }
  } else if (typeof raw === "string") {
    const n = normalizeType(raw);
    if (n) values.push(n);
  }
  const seen = new Set<string>();
  const out: string[] = [];
  for (const t of values) {
    if (!seen.has(t)) {
      seen.add(t);
      out.push(t);
    }
  }
  return out;
}

export function familyFor(requested: string): Set<string> {
  const key = normalizeType(requested);
  if (COURSE_FAMILY.has(key)) return COURSE_FAMILY;
  if (LOCAL_BUSINESS_FAMILY.has(key)) return LOCAL_BUSINESS_FAMILY;
  if (key === "FAQPage") return new Set(["FAQPage"]);
  if (key === "Organization") {
    const set = new Set<string>();
    for (const t of ORGANIZATION_FAMILY) {
      if (!LOCAL_BUSINESS_FAMILY.has(t)) set.add(t);
    }
    return set;
  }
  if (key) return new Set([key]);
  return new Set();
}

export function matchesRequested(found: string[], requested: string[]): boolean {
  if (!requested.length) return true;
  return requested.some((r) => {
    const fam = familyFor(r);
    return found.some((ft) => fam.has(ft));
  });
}
