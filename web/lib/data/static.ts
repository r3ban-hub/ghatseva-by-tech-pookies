// Presentation text that is not data: display names, PRD v2 rule and window descriptions,
// role examples and estimator line items. No figure, flag, date, reading or action here —
// those come from the backend export (lib/data/generated/backend.json).

import type { EstimateLine, Localized, Phase, Season, TaskGroupInfo, WorkOrderMeta } from "./types";

/** Display names per standard site name (track CSV `site`). The backend decides which sites exist. */
export const SITE_LABELS: Record<string, { siteId: string; hi: string }> = {
  "Bairagarh (Sant Hirdaram) kund": { siteId: "bairagarh", hi: "बैरागढ़ (संत हिरदाराम) कुंड" },
  "Malikhedi kund": { siteId: "malikhedi", hi: "मालीखेड़ी कुंड" },
  "Khatlapura ghat": { siteId: "khatlapura", hi: "खटलापुरा घाट" },
  "Rani Kamlapati ghat / Kamla Park kund": { siteId: "rani-kamlapati", hi: "रानी कमलापति घाट / कमला पार्क कुंड" },
  "Shahpura lake ghat": { siteId: "shahpura", hi: "शाहपुरा झील घाट" },
  "Prempura ghat": { siteId: "prempura", hi: "प्रेमपुरा घाट" },
  "Hathaikheda dam / kund": { siteId: "hathaikheda", hi: "हथाईखेड़ा डैम / कुंड" },
};

export const WATER_BODY_HI: Record<string, string> = {
  "Upper Lake": "बड़ा तालाब (अपर लेक)",
  "Lower Lake": "छोटा तालाब (लोअर लेक)",
  "Lower Lake (as printed in Durga tables)": "छोटा तालाब (दुर्गा तालिकाओं में जैसा छपा)",
  Kund: "कुंड",
  "Shahpura Lake": "शाहपुरा झील",
  "Hathaikheda dam": "हथाईखेड़ा डैम",
};

export const PARAMETER_LABELS: Record<string, Localized> = {
  "Dissolved oxygen": { en: "Dissolved oxygen (DO)", hi: "घुलित ऑक्सीजन (DO)" },
  BOD: { en: "BOD", hi: "BOD" },
  pH: { en: "pH", hi: "pH" },
  "Total coliform": { en: "Total coliform", hi: "टोटल कोलीफॉर्म" },
};

// Expected grid layout (data dictionary): Ganesh before Durga within each year.
export const SEASONS: Season[] = [
  { year: 2023, festival: "Ganesh" },
  { year: 2023, festival: "Durga" },
  { year: 2024, festival: "Ganesh" },
  { year: 2024, festival: "Durga" },
  { year: 2025, festival: "Ganesh" },
  { year: 2025, festival: "Durga" },
];
export const PHASES: Phase[] = ["pre", "during", "after"];
export const PARAMETERS = [
  "pH", "Dissolved oxygen", "BOD", "COD", "Total solids", "Dissolved solids", "Suspended solids",
  "Turbidity", "Conductivity", "Chromium", "Lead", "Zinc", "Copper",
];

export const DATA_WINDOW: Localized = {
  en: "MPPCB visarjan reports 2023–2025 · Ganesh and Durga · before, during and one week after immersion",
  hi: "MPPCB विसर्जन रिपोर्ट 2023–2025 · गणेश और दुर्गा · विसर्जन से पहले, दौरान और एक सप्ताह बाद",
};

export const SOURCE_LABEL: Localized = {
  en: "Backend output: computed by the Visarjan Ghat Watch Python pipeline from the supplied track CSV and CPCB criteria file.",
  hi: "बैकएंड आउटपुट: विसर्जन घाट वॉच की Python पाइपलाइन ने दिए गए ट्रैक CSV और CPCB मानदंड फ़ाइल से गणना की।",
};

/** PRD v2 §7.3 window descriptions, in window order. Dates come from the backend plan. */
export const PLAN_WINDOW_TEXT: { label: string; activities: Localized }[] = [
  {
    label: "D-9 → D-7",
    activities: {
      en: "Officer approves the priority list. Field check of Rani Kamlapati / Kamla Park identity. Request pre-immersion sampling at data-gap ghats.",
      hi: "अधिकारी प्राथमिकता सूची स्वीकृत करें। रानी कमलापति / कमला पार्क की पहचान की फ़ील्ड जाँच। डेटा-कमी वाले घाटों पर विसर्जन-पूर्व नमूने का अनुरोध।",
    },
  },
  {
    label: "D-6 → D-3",
    activities: {
      en: "Pre-immersion sampling. Install barricades, nets or booms. Set up flower and offering collection points. Arrange aerators for Tier 1 ghats.",
      hi: "विसर्जन-पूर्व नमूना। बैरिकेड, जाल या बूम लगाएँ। फूल और चढ़ावा संग्रह केंद्र बनाएँ। टियर 1 घाटों के लिए एरेटर की व्यवस्था।",
    },
  },
  {
    label: "D-2 → D-1",
    activities: {
      en: "Aerators running at ghats with DO below 4 in past readings. Crews briefed and deployed. Re-check DO at Tier 1.",
      hi: "पिछली रीडिंग में DO 4 से कम वाले घाटों पर एरेटर चालू। दल को जानकारी देकर तैनात करें। टियर 1 पर DO की दोबारा जाँच।",
    },
  },
  {
    label: "D",
    activities: {
      en: "Immersion. During-immersion sampling. Aeration on. Continuous removal of floating debris.",
      hi: "विसर्जन। विसर्जन के दौरान नमूना। एरेशन चालू। तैरते मलबे को लगातार हटाना।",
    },
  },
  {
    label: "D+1 → D+2",
    activities: {
      en: "Post-visarjan clean-up: remove idol remnants, frames, cloth and floral waste; transport for disposal. Aeration continues.",
      hi: "विसर्जन के बाद सफ़ाई: मूर्ति अवशेष, ढाँचे, कपड़ा और फूलों का कचरा हटाएँ; निपटान के लिए ले जाएँ। एरेशन जारी।",
    },
  },
  {
    label: "D+3 → D+6",
    activities: {
      en: "Follow-up DO checks at high-risk ghats; residual clean-up.",
      hi: "उच्च जोखिम घाटों पर अनुवर्ती DO जाँच; बची हुई सफ़ाई।",
    },
  },
  {
    label: "D+7",
    activities: {
      en: "One-week-after sampling, including coliform. Status against the one-week-after target. Officer report.",
      hi: "एक सप्ताह बाद नमूना, कोलीफॉर्म सहित। एक सप्ताह बाद के लक्ष्य के सापेक्ष स्थिति। अधिकारी रिपोर्ट।",
    },
  },
];

// PRD v2 §7.4: role titles are examples only. Nothing is assigned until the officer fills it in.
export const TASK_GROUPS: TaskGroupInfo[] = [
  {
    group: "aeration",
    roleExample: { en: "e.g. Zone engineer (water works)", hi: "उदा. ज़ोन इंजीनियर (जल कार्य)" },
    outcome: { en: "Report aerator start and stop dates and the DO checks taken.", hi: "एरेटर शुरू और बंद होने की तिथियाँ और ली गई DO जाँच बताएँ।" },
  },
  {
    group: "cleaning",
    roleExample: { en: "e.g. Zone sanitation in-charge", hi: "उदा. ज़ोन स्वच्छता प्रभारी" },
    outcome: {
      en: "Tick sheet, photos before and after, and quantity of debris removed if measured.",
      hi: "टिक शीट, पहले और बाद की तस्वीरें, और हटाए गए मलबे की मात्रा (यदि मापी गई)।",
    },
  },
  {
    group: "barricading",
    roleExample: { en: "e.g. Zone engineer (civil)", hi: "उदा. ज़ोन इंजीनियर (सिविल)" },
    outcome: { en: "Barricades, nets or booms in place before immersion day; photos.", hi: "विसर्जन के दिन से पहले बैरिकेड, जाल या बूम लगे हों; तस्वीरें।" },
  },
  {
    group: "sampling",
    roleExample: { en: "e.g. MPPCB regional office, Bhopal (assumption)", hi: "उदा. MPPCB क्षेत्रीय कार्यालय, भोपाल (अनुमान)" },
    outcome: {
      en: "DO, BOD and pH results (plus total coliform where requested) recorded with sample date.",
      hi: "DO, BOD और pH के परिणाम (अनुरोध पर टोटल कोलीफॉर्म भी) नमूना तिथि के साथ दर्ज।",
    },
  },
  {
    group: "identity",
    roleExample: { en: "Officer to assign", hi: "अधिकारी निर्धारित करें" },
    outcome: { en: "Location sampled under this name confirmed and recorded.", hi: "इस नाम से नमूना लिए जाने वाले स्थान की पुष्टि दर्ज।" },
  },
];

export const WORK_ORDER_META: WorkOrderMeta = {
  issuedByRole: { en: "Visarjan nodal officer, BMC (role; assumption)", hi: "विसर्जन नोडल अधिकारी, BMC (पद; अनुमान)" },
  // The backend leaves the report-back date to the officer; no date is invented here.
  reportBackBy: { en: "________ (date set by the nodal officer)", hi: "________ (तिथि नोडल अधिकारी तय करें)" },
  reportBackItems: [
    { en: "Tick sheet of tasks done", hi: "किए गए कार्यों की टिक शीट" },
    { en: "Photos before and after", hi: "पहले और बाद की तस्वीरें" },
    { en: "Dates the aerators started and stopped", hi: "एरेटर शुरू और बंद होने की तिथियाँ" },
    { en: "Quantity of debris removed, if measured", hi: "हटाए गए मलबे की मात्रा, यदि मापी गई" },
  ],
  provenance: "prd",
  prdRef: "PRD v2 §7.4",
};

// PRD v2 §8.3 line items. No rates are supplied, and none are invented.
export const ESTIMATE_LINES: EstimateLine[] = [
  { id: "labour", item: { en: "Unskilled labour", hi: "अकुशल श्रमिक" }, unit: { en: "worker-day", hi: "श्रमिक-दिन" } },
  { id: "supervisor", item: { en: "Supervisor", hi: "पर्यवेक्षक" }, unit: { en: "person-day", hi: "व्यक्ति-दिन" } },
  { id: "aerator", item: { en: "Aerator hire incl. power", hi: "एरेटर किराया (बिजली सहित)" }, unit: { en: "unit-day", hi: "यूनिट-दिन" } },
  { id: "meter", item: { en: "Portable DO meter / test kit", hi: "पोर्टेबल DO मीटर / टेस्ट किट" }, unit: { en: "unit", hi: "यूनिट" } },
  { id: "lab", item: { en: "Lab test (DO, BOD, pH, coliform)", hi: "प्रयोगशाला परीक्षण (DO, BOD, pH, कोलीफॉर्म)" }, unit: { en: "sample", hi: "नमूना" } },
  { id: "transport", item: { en: "Debris transport", hi: "मलबा परिवहन" }, unit: { en: "trip", hi: "फेरा" } },
  { id: "nets", item: { en: "Nets / booms / barricades", hi: "जाल / बूम / बैरिकेड" }, unit: { en: "ghat", hi: "घाट" } },
];

/** PRD v2 §7.1 status rules for the one-week-after sample (descriptions only). */
export const TARGET_STATUSES: { id: string; label: Localized; rule: Localized }[] = [
  {
    id: "meets",
    label: { en: "Meets measured Class B criteria", hi: "मापे गए क्लास B मानकों पर खरा" },
    rule: {
      en: "DO, BOD and pH all within limits in the one-week-after sample. Total coliform still needs a test to confirm Class B.",
      hi: "एक सप्ताह बाद के नमूने में DO, BOD और pH तीनों सीमा में। क्लास B की पुष्टि के लिए टोटल कोलीफॉर्म का परीक्षण अभी भी ज़रूरी।",
    },
  },
  {
    id: "baseline",
    label: { en: "Back to pre-immersion level (interim)", hi: "विसर्जन-पूर्व स्तर पर वापस (अंतरिम)" },
    rule: {
      en: "Fails Class B, but DO is at or above and BOD at or below that season's pre-immersion reading.",
      hi: "क्लास B पर खरा नहीं, लेकिन DO उस सीज़न की विसर्जन-पूर्व रीडिंग के बराबर या अधिक और BOD बराबर या कम।",
    },
  },
  {
    id: "not-met",
    label: { en: "Does not meet", hi: "मानक पूरा नहीं" },
    rule: { en: "DO, BOD or pH outside limits and worse than pre-immersion.", hi: "DO, BOD या pH सीमा से बाहर और विसर्जन-पूर्व से खराब।" },
  },
  {
    id: "cannot-assess",
    label: { en: "Cannot assess", hi: "आकलन संभव नहीं" },
    rule: { en: "DO, BOD or pH missing from the sample.", hi: "नमूने में DO, BOD या pH अनुपलब्ध।" },
  },
];
