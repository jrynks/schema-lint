export type Fixture = {
  id: string;
  label: string;
  hint: string;
  expect: "OK" | "ERRORS";
  html: string;
};

export const FIXTURES: Fixture[] = [
  {
    id: "faq-valid",
    label: "FAQPage valid",
    hint: "Two questions with answers",
    expect: "OK",
    html: `<!doctype html><html><head><script type="application/ld+json">
{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
  {"@type":"Question","name":"What is a course refund policy?","acceptedAnswer":{"@type":"Answer","text":"Refunds are issued within 14 days of purchase."}},
  {"@type":"Question","name":"Do you offer evening classes?","acceptedAnswer":{"@type":"Answer","text":"Yes, Tuesday and Thursday evenings."}}
]}
</script></head><body><h1>FAQ</h1></body></html>`,
  },
  {
    id: "faq-missing",
    label: "FAQ missing answer",
    hint: "Question with no acceptedAnswer",
    expect: "ERRORS",
    html: `<!doctype html><html><head><script type="application/ld+json">
{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":"What is a course refund policy?"}]}
</script></head><body></body></html>`,
  },
  {
    id: "broken",
    label: "Broken JSON-LD",
    hint: "Unclosed array — parse error",
    expect: "ERRORS",
    html: `<!doctype html><html><head><script type="application/ld+json">
{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
</script></head><body></body></html>`,
  },
  {
    id: "lb-missing",
    label: "LocalBusiness empty",
    hint: "Missing name, address, telephone",
    expect: "ERRORS",
    html: `<!doctype html><html><head><script type="application/ld+json">
{"@context":"https://schema.org","@type":"LocalBusiness","priceRange":"$$"}
</script></head><body></body></html>`,
  },
  {
    id: "course-min",
    label: "Course minimal",
    hint: "name + description + provider",
    expect: "OK",
    html: `<!doctype html><html><head><script type="application/ld+json">
{"@context":"https://schema.org","@type":"Course","name":"Intro to Bookkeeping","description":"A four-week primer on small-business bookkeeping.","provider":{"@type":"Organization","name":"North Shore Ledger"}}
</script></head><body></body></html>`,
  },
  {
    id: "dentist",
    label: "Dentist complete",
    hint: "LocalBusiness family subtype",
    expect: "OK",
    html: `<!doctype html><html><head><script type="application/ld+json">
{"@context":"https://schema.org","@type":"Dentist","name":"Cedar Smile Dental","telephone":"+1-604-555-0142","url":"https://cedar.example/dental","image":"https://cedar.example/office.jpg","priceRange":"$$","address":{"@type":"PostalAddress","streetAddress":"2100 Shaughnessy St","addressLocality":"Port Coquitlam","addressRegion":"BC","postalCode":"V3C 2Z5","addressCountry":"CA"},"geo":{"@type":"GeoCoordinates","latitude":49.262,"longitude":-122.781},"openingHours":"Mo-Fr 09:00-17:00"}
</script></head><body></body></html>`,
  },
  {
    id: "graph",
    label: "@graph mixed",
    hint: "WebSite + Course + BreadcrumbList",
    expect: "OK",
    html: `<!doctype html><html><head><script type="application/ld+json">
{"@context":"https://schema.org","@graph":[
  {"@type":"WebSite","name":"North Shore Ledger","url":"https://ledger.example"},
  {"@type":["Course","Product"],"name":"Payroll Lab","about":"Hands-on payroll workshop","author":"Ada Book","url":"https://ledger.example/payroll","offers":{"@type":"Offer","price":"249","priceCurrency":"CAD"},"hasCourseInstance":{"@type":"CourseInstance","startDate":"2026-10-01","endDate":"2026-10-04","courseMode":"onsite"}},
  {"@type":"BreadcrumbList","itemListElement":[
    {"@type":"ListItem","position":1,"name":"Home","item":"https://ledger.example/"},
    {"@type":"ListItem","position":2,"name":"Courses","item":"https://ledger.example/courses"}
  ]}
]}
</script></head><body></body></html>`,
  },
];
