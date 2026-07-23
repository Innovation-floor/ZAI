"""Authored seed records from the ZAI Master Project Database (fictional/illustrative)."""

SEED = [
    (1,"Amman Family Water Access Program","Jordan","Middle East & North Africa","Water & Sanitation","Active","WaterFirst Alliance",12.4,38000,78,"Low",2024,2026,[6,3],"Rehabilitates community wells and household connections across greater Amman, reducing waterborne illness and cutting daily water-collection time for families."),
    (2,"Zarqa Vocational Skills Initiative","Jordan","Middle East & North Africa","Livelihoods","Active","Horizon Development Partners",6.8,4200,55,"Low",2025,2026,[8,4],"Trains young adults and refugees in trades such as electrical work, tailoring and food processing, linking graduates to local employers."),
    (3,"Beirut School Rebuilding Project","Lebanon","Middle East & North Africa","Education","Active","EduReach Network",18.2,9600,64,"Medium",2024,2026,[4,11],"Repairs and re-equips public schools damaged by economic and infrastructure crises, restoring safe learning spaces for children."),
    (4,"Gaza Emergency Medical Corridor","Palestine","Middle East & North Africa","Emergency Relief","Active","MedAid Global",24.6,61000,41,"High",2025,2026,[3,16],"Supplies mobile clinics, trauma kits and emergency staffing to under-resourced health facilities in high-need districts."),
    (5,"Idlib Winter Shelter Response","Syria","Middle East & North Africa","Shelter & Reconstruction","Active","Shelter Now Coalition",15.1,22500,70,"High",2023,2025,[1,11],"Provides insulated shelter units and winterization kits to displaced families ahead of the harsh northern-Syria winter season."),
    (6,"Sana'a Nutrition Recovery Program","Yemen","Middle East & North Africa","Health & Nutrition","Active","MedAid Global",9.7,17800,60,"High",2024,2026,[2,3],"Screens and treats acute malnutrition in children under five through mobile health units and community outreach workers."),
    (7,"Nile Delta Irrigation Renewal","Egypt","Middle East & North Africa","Water & Sanitation","Completed","WaterFirst Alliance",21.3,46000,100,"Low",2022,2024,[6,2],"Modernized irrigation canals for smallholder farmers, improving crop yields and reducing water waste across three governorates."),
    (8,"Atlas Orphan Care Network","Morocco","Middle East & North Africa","Orphan & Family Care","Active","Bright Future Initiative",5.4,1300,82,"Low",2023,2026,[1,10],"Supports orphaned and vulnerable children with housing, schooling stipends and family reintegration case management."),
    (9,"Tunis Coastal Livelihoods Program","Tunisia","Middle East & North Africa","Livelihoods","Planning","Unity Relief Corps",4.9,2600,8,"Medium",2026,2028,[8,14],"Planned initiative to support small-scale fishing cooperatives with equipment grants and cold-storage infrastructure."),
    (10,"Turkana Water Security Program","Kenya","Sub-Saharan Africa","Water & Sanitation","Active","WaterFirst Alliance",14.9,52000,47,"Medium",2024,2026,[6,13],"Drills solar-powered boreholes across drought-prone Turkana County and trains local committees to manage them."),
    (11,"Mogadishu Displacement Response","Somalia","Sub-Saharan Africa","Emergency Relief","Active","Unity Relief Corps",19.8,73000,35,"High",2025,2026,[1,16],"Delivers emergency food, water and shelter to families displaced by drought and conflict in and around Mogadishu."),
    (12,"Darfur Community Health Posts","Sudan","Sub-Saharan Africa","Health & Nutrition","Active","MedAid Global",13.5,29000,52,"High",2024,2026,[3],"Establishes basic health posts staffed by trained community health workers in hard-to-reach displacement settlements."),
    (13,"Sahel Girls' Education Bridge","Mali","Sub-Saharan Africa","Education","Active","EduReach Network",8.3,6100,58,"Medium",2024,2026,[4,5],"Builds temporary learning spaces and provides scholarships to keep girls enrolled through conflict-related school closures."),
    (14,"Lake Chad Basin Food Resilience","Chad","Sub-Saharan Africa","Food Security","Active","Bridge to Hope",11.2,34500,44,"Medium",2024,2026,[2,13],"Distributes drought-resistant seed and farming tools while running cash-for-work programs during the lean season."),
    (15,"Comoros Coastal Rebuilding Initiative","Comoros","Sub-Saharan Africa","Shelter & Reconstruction","Completed","Shelter Now Coalition",3.6,2100,100,"Low",2023,2024,[11,13],"Rebuilt homes and community shelters following cyclone damage along the northern coastline."),
    (16,"Cox's Bazar Learning Centers","Bangladesh","South & Southeast Asia","Education","Active","EduReach Network",10.6,27000,66,"Medium",2023,2026,[4],"Operates informal learning centers for refugee children, focusing on literacy, numeracy and psychosocial support."),
    (17,"Sindh Flood Recovery Program","Pakistan","South & Southeast Asia","Shelter & Reconstruction","Active","Shelter Now Coalition",17.4,41000,61,"Medium",2024,2026,[1,11],"Rebuilds flood-damaged housing and irrigation infrastructure across rural districts of Sindh province."),
    (18,"Aceh Clean Water Expansion","Indonesia","South & Southeast Asia","Water & Sanitation","Completed","WaterFirst Alliance",7.1,19500,100,"Low",2022,2023,[6],"Extended piped water access to coastal villages, reducing reliance on contaminated surface water sources."),
    (19,"Mindanao Livelihoods Recovery","Philippines","South & Southeast Asia","Livelihoods","Active","Horizon Development Partners",6.2,8800,49,"Medium",2024,2026,[8,1],"Provides microgrants and business training to families rebuilding income sources after conflict displacement."),
    (20,"Kathmandu Valley School Retrofit","Nepal","South & Southeast Asia","Education","Active","EduReach Network",9.0,12300,73,"Low",2023,2025,[4,11],"Retrofits earthquake-vulnerable school buildings and trains staff in disaster preparedness."),
    (21,"Herat Winter Relief Program","Afghanistan","South & Southeast Asia","Emergency Relief","Active","Bridge to Hope",16.0,54000,39,"High",2025,2026,[1,3],"Distributes fuel, blankets and emergency cash assistance to vulnerable households through the winter months."),
]

COUNTRY_META = {
    "Jordan":        (31.95, 35.93, "الأردن"),
    "Lebanon":       (33.89, 35.50, "لبنان"),
    "Palestine":     (31.52, 34.45, "فلسطين"),
    "Syria":         (35.93, 36.63, "سوريا"),
    "Yemen":         (15.35, 44.21, "اليمن"),
    "Egypt":         (30.80, 31.10, "مصر"),
    "Morocco":       (31.63, -7.99, "المغرب"),
    "Tunisia":       (36.81, 10.18, "تونس"),
    "Kenya":         (3.12,  35.60, "كينيا"),
    "Somalia":       (2.05,  45.32, "الصومال"),
    "Sudan":         (13.63, 25.35, "السودان"),
    "Mali":          (16.77, -3.00, "مالي"),
    "Chad":          (13.45, 14.53, "تشاد"),
    "Comoros":       (-11.70, 43.25, "جزر القمر"),
    "Bangladesh":    (21.43, 92.01, "بنغلاديش"),
    "Pakistan":      (25.87, 68.50, "باكستان"),
    "Indonesia":     (5.55,  95.32, "إندونيسيا"),
    "Philippines":   (7.19, 124.24, "الفلبين"),
    "Nepal":         (27.71, 85.32, "نيبال"),
    "Afghanistan":   (34.35, 62.20, "أفغانستان"),
    "Iraq":          (33.31, 44.36, "العراق"),
    "Ethiopia":      (9.15,  40.49, "إثيوبيا"),
    "Niger":         (13.51,  2.11, "النيجر"),
    "Sri Lanka":     (7.87,  80.77, "سريلانكا"),
}

EXTRA_REGION = {
    "Iraq": "Middle East & North Africa",
    "Ethiopia": "Sub-Saharan Africa",
    "Niger": "Sub-Saharan Africa",
    "Sri Lanka": "South & Southeast Asia",
}

PARTNER_POOL_PREFIX = [
    "Al Noor", "Sahara", "Crescent", "Horizon", "Northern", "Coastal", "Cedar",
    "Delta", "Highland", "Meridian", "Oasis", "Pioneer", "Riverbank", "Summit",
    "Unity", "Valley", "Anchor", "Beacon", "Compass", "Dawn",
]
PARTNER_POOL_SUFFIX = ["Relief Trust", "Development Fund", "Aid Foundation"]

SECTOR_AR = {
    "Water & Sanitation": "المياه والصرف الصحي",
    "Livelihoods": "سبل العيش",
    "Education": "التعليم",
    "Emergency Relief": "الإغاثة الطارئة",
    "Shelter & Reconstruction": "المأوى وإعادة الإعمار",
    "Health & Nutrition": "الصحة والتغذية",
    "Orphan & Family Care": "رعاية الأيتام والأسرة",
    "Food Security": "الأمن الغذائي",
}

STATUS_AR = {"Active": "نشط", "Completed": "مكتمل", "Planning": "قيد التخطيط"}
RISK_AR = {"Low": "منخفض", "Medium": "متوسط", "High": "مرتفع"}

OPERATING_CONTEXT = {
    "Jordan": {
        "challenges": ["Rising operating costs in host communities with large refugee populations",
                       "Permit renewal cycles for infrastructure works can extend timelines"],
        "entities": ["Ministry of Social Development liaison office", "Municipal water authorities"],
        "friction": ["Cross-agency data-sharing is inconsistent between municipalities"],
        "decision_note": "Stable regulatory environment with strong local partner capacity; a good candidate for scaling successful pilots to neighbouring host communities.",
    },
    "Kenya": {
        "challenges": ["Drought cycles affect borehole yield predictability",
                       "Remote site logistics increase maintenance response time"],
        "entities": ["County water resource offices", "Community water management committees"],
        "friction": ["Some committees require refresher training after leadership changes"],
        "decision_note": "Solar-borehole model is performing well; pair future rollouts with a committee-retention program to protect long-term maintenance quality.",
    },
}

OPERATING_CONTEXT.update({
    "Palestine": {
        "challenges": ["Movement and access restrictions limit predictable delivery windows",
                       "Damaged infrastructure increases cost and time for basic repairs"],
        "entities": ["Local health directorate", "International medical coordination cell"],
        "friction": ["Access approvals for supply convoys can be delayed"],
        "decision_note": "Maintain flexible logistics buffers and pre-positioned stock; prioritise partners experienced in access negotiation.",
    },
    "Syria": {
        "challenges": ["Security conditions vary significantly by district and season",
                       "Cross-border logistics require multiple layers of approval"],
        "entities": ["Local shelter cluster coordination group", "Cross-border logistics partners"],
        "friction": ["Registration and access permissions differ by governing authority"],
        "decision_note": "Build in seasonal contingency for winterisation work; diversify supply routes to reduce single-corridor dependency.",
    },
    "Somalia": {
        "challenges": ["Security clearance requirements limit access to some displacement sites",
                       "Displacement patterns shift faster than planning cycles"],
        "entities": ["Local displacement-site committees", "Mobile money service providers"],
        "friction": ["Access negotiations can outlast the emergency response window"],
        "decision_note": "Shift a larger share of the response toward mobile-money cash assistance, which delivers faster than in-kind distribution here.",
    },
    "Egypt": {
        "challenges": ["Bureaucratic approval chains for large infrastructure works",
                       "Water allocation coordination across multiple governorates"],
        "entities": ["Governorate irrigation authorities", "Farmer cooperatives"],
        "friction": ["Multi-governorate projects require sequential sign-offs"],
        "decision_note": "Track record of on-time completion; a strong candidate for a repeatable programme model in other irrigation-dependent regions.",
    },
    "Bangladesh": {
        "challenges": ["High population density in camp settings strains learning-space capacity",
                       "Monsoon season limits construction and outreach windows"],
        "entities": ["Camp-level education coordination group", "Community learning facilitators"],
        "friction": ["Facility expansion approvals involve multiple coordinating bodies"],
        "decision_note": "Strong enrolment outcomes; psychosocial support components appear to be the key driver of retention.",
    },
    "Afghanistan": {
        "challenges": ["Winter access windows are short and weather-dependent",
                       "Currency and banking constraints affect cash-assistance delivery"],
        "entities": ["Community distribution committees", "Local relief coordination office"],
        "friction": ["Cash-assistance delivery channels are limited in some districts"],
        "decision_note": "Front-load procurement before winter access closes; explore voucher-based alternatives where cash channels are constrained.",
    },
    "Pakistan": {
        "challenges": ["Recurrent flood risk affects reconstruction site selection",
                       "Rural road access can be seasonal in affected districts"],
        "entities": ["Provincial disaster management authority", "Village reconstruction committees"],
        "friction": ["Material transport is weather-dependent in monsoon months"],
        "decision_note": "Make flood-resilient building standards the default rather than optional, given the recurrence pattern in this province.",
    },
})

DEFAULT_CONTEXT = {
    "challenges": ["Access and logistics constraints affect delivery predictability"],
    "entities": ["Local coordination committees", "Regional authorities"],
    "friction": ["Approval timelines vary by authority"],
    "decision_note": "Maintain flexible delivery planning and diversify implementation routes.",
}
