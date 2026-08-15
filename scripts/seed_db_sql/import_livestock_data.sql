-- GENERATED FILE: do not edit manually.

-- Regenerate with scripts/livestock/generate_seed_sql.py.

-- Destructive source DDL is not included; all reviewed data rows are included.

-- 02_insert_livestock_catalog.sql SHA-256: d79ac1d2ff564ced39d42571f9d5553634255a48e9a48463fc016af401fe24f8

-- 03_insert_livestock_population.sql SHA-256: d87cc0219b61e653a6c9c43e4da40b9eeb3c68893a9bf60be2f14f7c694fd806

-- 04_insert_livestock_breed.sql SHA-256: 780a0fde286994e13062a66ea61a045abb27ca41d0ecc50a826eaf39ca28ee9e

-- 05_insert_livestock_reference.sql SHA-256: 6419165131c93bff958f168d211c078b6b847df5e79379a390f4433a5beb8bcc

-- 06_insert_livestock_registry.sql SHA-256: dddc4be6e335f0dc257c1541c1eca655518feb709ab5ea6888ab22e5ba39cc7f

INSERT INTO g2p_livestock_type (species_code, name, description, icon_url, dataset_id, scientific_name, subfamily, species_type_code, chart_color, ear_tag_range, in_lis_population, in_etlits_registry) VALUES
  ('beehive', 'Beehive', 'Managed honey bee colony unit registered in ET-LITS. Bees are listed as a domestic animal species in the National Livestock Data Standard but are not tracked on the LIS population dashboard.', NULL, NULL, 'Anthophila', 'Apinae', NULL, NULL, NULL, FALSE, TRUE),
  ('camel', 'Camel', 'Arid-zone livestock species tracked in Ethiopia''s national population dashboard.', 'https://lis.moa.gov.et/wp/wp-content/uploads/2025/05/camel-population.svg', 61, 'Camelus', 'Camelidae', 4, '#EA901C', 'ET 7500000000-ET 7599999999', TRUE, TRUE),
  ('cattle', 'Cattle', 'A vital livestock species in Ethiopia, including zebu cattle known for resilience to harsh climates and a crucial role in agriculture and livelihoods.', 'https://lis.moa.gov.et/wp/wp-content/uploads/2025/05/cattle-population.svg', 61, 'Bos taurus & Bos indicus', 'Bovine', 1, '#484848', 'ET 0000000000-ET 4999999999', TRUE, TRUE),
  ('goat', 'Goat', 'Major small ruminant livestock species tracked in Ethiopia''s national population dashboard.', 'https://lis.moa.gov.et/wp/wp-content/uploads/2025/05/goat-population.svg', 61, 'Capra hircus', 'Caprine', 2, '#FACE58', 'ET 6000000000-ET 7499999999', TRUE, TRUE),
  ('sheep', 'Sheep', 'Major small ruminant livestock species tracked in Ethiopia''s national population dashboard.', 'https://lis.moa.gov.et/wp/wp-content/uploads/2025/05/sheep-population.svg', 61, 'Ovis aries', 'Ovine', 3, '#BA4747', 'ET 5000000000-ET 5999999999', TRUE, TRUE)
ON CONFLICT (species_code) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    icon_url = EXCLUDED.icon_url,
    dataset_id = EXCLUDED.dataset_id,
    scientific_name = EXCLUDED.scientific_name,
    subfamily = EXCLUDED.subfamily,
    species_type_code = EXCLUDED.species_type_code,
    chart_color = EXCLUDED.chart_color,
    ear_tag_range = EXCLUDED.ear_tag_range,
    in_lis_population = EXCLUDED.in_lis_population,
    in_etlits_registry = EXCLUDED.in_etlits_registry;

SELECT setval('g2p_livestock_type_id_seq', (SELECT MAX(id) FROM g2p_livestock_type), TRUE);

INSERT INTO g2p_livestock_population (species_code, census_year, population_total, source_record_count)
SELECT species.id, source.census_year, source.population_total, source.source_record_count
FROM (VALUES
  ('camel', 2011, 1102095, 56),
  ('camel', 2012, 2520724, 114),
  ('camel', 2014, 1098290, 54),
  ('camel', 2016, 1210336, 54),
  ('camel', 2017, 1204985, 52),
  ('camel', 2018, 1418435, 50),
  ('camel', 2019, 3172630, 58),
  ('camel', 2020, 3729322, 164),
  ('camel', 2021, 8145756, 166),
  ('camel', 2022, 6979212, 158),
  ('cattle', 2011, 53382128, 138),
  ('cattle', 2012, 54832951, 136),
  ('cattle', 2014, 55027213, 132),
  ('cattle', 2016, 59486601, 132),
  ('cattle', 2017, 59486601, 132),
  ('cattle', 2018, 60391952, 132),
  ('cattle', 2019, 59626205, 156),
  ('cattle', 2020, 61591086, 164),
  ('cattle', 2021, 70291692, 166),
  ('cattle', 2022, 66272429, 158),
  ('goat', 2011, 22786883, 138),
  ('goat', 2012, 33798728, 136),
  ('goat', 2014, 28163269, 132),
  ('goat', 2016, 30200161, 132),
  ('goat', 2017, 30200161, 132),
  ('goat', 2018, 32738317, 132),
  ('goat', 2019, 50957330, 156),
  ('goat', 2020, 36805893, 164),
  ('goat', 2021, 52463454, 166),
  ('goat', 2022, 45788648, 158),
  ('sheep', 2011, 25508939, 138),
  ('sheep', 2012, 27430649, 136),
  ('sheep', 2014, 27347871, 132),
  ('sheep', 2016, 30697879, 132),
  ('sheep', 2017, 30697879, 132),
  ('sheep', 2018, 31302190, 132),
  ('sheep', 2019, 35494018, 156),
  ('sheep', 2020, 32855473, 164),
  ('sheep', 2021, 42914785, 166),
  ('sheep', 2022, 38036905, 158)
) AS source (source_species_code, census_year, population_total, source_record_count)
JOIN g2p_livestock_type species
  ON species.species_code = source.source_species_code
ON CONFLICT (species_code, census_year) DO UPDATE SET
    population_total = EXCLUDED.population_total,
    source_record_count = EXCLUDED.source_record_count;

INSERT INTO g2p_livestock_breed (id, breed_code, name, abbreviation, species_id, breed_type, in_national_standard, in_etlits_registry, source)
SELECT source.id, source.breed_code, source.name, source.abbreviation, species.id, source.breed_type, source.in_national_standard, source.in_etlits_registry, source.source_name
FROM (VALUES
  (1, '1.01.01', 'Abergele', 'ABE', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (2, '1.01.02', 'Abigar', 'ABI', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (3, '1.01.03', 'Adwa', 'ADW', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (4, '1.01.04', 'Afar', 'AFA', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (5, '1.01.05', 'Ambo', 'AMB', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (6, '1.01.06', 'Arado', 'ARA', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (7, '1.01.07', 'Arsi', 'ARS', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (8, '1.01.08', 'Bale', 'BAL', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (9, '1.01.09', 'Begait', 'BEGc', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (10, '1.01.10', 'Boran', 'BOR', 'cattle', 'Indigenous', TRUE, TRUE, 'National Livestock Data Standard (MOA, 2024)'),
  (11, '1.01.11', 'Fogera', 'FOG', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (12, '1.01.12', 'Goffa', 'GOF', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (13, '1.01.13', 'Guraghe', 'GUR', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (14, '1.01.14', 'Hammer', 'HAM', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (15, '1.01.15', 'Harar', 'HAR', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (16, '1.01.16', 'Horro', 'HORc', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (17, '1.01.17', 'Jem-Jem Zebu', 'JEM', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (18, '1.01.18', 'Jiddu', 'JID', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (19, '1.01.19', 'Jijjiga', 'JIJ', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (20, '1.01.20', 'Medenes', 'MED', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (21, '1.01.21', 'Mursi', 'MUR', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (22, '1.01.22', 'Ogaden', 'OGA', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (23, '1.01.23', 'Raya Azebo', 'RAY-A', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (24, '1.01.24', 'Sheko', 'SHE', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (25, '1.01.25', 'Smada', 'SMA', 'cattle', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (26, '1.02.01', 'Holstein Friesian', 'HOL', 'cattle', 'Exotic', TRUE, TRUE, 'National Livestock Data Standard (MOA, 2024)'),
  (27, '1.02.02', 'Jersey', 'JER', 'cattle', 'Exotic', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (28, '1.02.03', 'Simmental', 'SIM', 'cattle', 'Exotic', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (29, '1.02.04', 'Ayrshire', 'AYR', 'cattle', 'Exotic', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (30, '1.03.02.01-01.16', 'Holstein Friesian x Horro', 'HOL-HOR', 'cattle', 'Cross', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (31, '1.03.02.02-01.07', 'Jersey x Arsi', 'JER-ARS', 'cattle', 'Cross', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (32, '1.03.02.02-01.16', 'Jersey x Horro', 'JER-HOR', 'cattle', 'Cross', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (33, '1.03.02.03-01.10', 'Simmental x Boran', 'SIM-BOR', 'cattle', 'Cross', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (34, '1.03.02.03-01.16', 'Simmental x Horro', 'SIM-HOR', 'cattle', 'Cross', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (35, '2.01.01', 'Abergele', 'ABEg', 'goat', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (36, '2.01.02', 'Afar', 'AFAg', 'goat', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (37, '2.01.03', 'Agew', 'AGE', 'goat', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (38, '2.01.04', 'Arab', 'ARA', 'goat', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (39, '2.01.05', 'Arsi-Bale', 'ARS-BAL', 'goat', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (40, '2.01.06', 'Begayit', 'BEGg', 'goat', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (41, '2.01.07', 'Central Highland', 'CEN-HIG', 'goat', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (42, '2.01.08', 'Felata', 'FEL', 'goat', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (43, '2.01.09', 'Gumuz', 'GUM', 'goat', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (44, '2.01.10', 'Hararghe Highland', 'HAR-HIG', 'goat', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (45, '2.01.11', 'Keffa', 'KEF', 'goat', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (46, '2.01.12', 'Ille', 'ILLg', 'goat', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (47, '2.01.13', 'Long eared Somali', 'LON-EAR-SOM', 'goat', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (48, '2.01.14', 'Maefur', 'MAE', 'goat', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (49, '2.01.15', 'Short eared Somali', 'SHO-EAR-SOM', 'goat', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (50, '2.01.16', 'Western Highland', NULL, 'goat', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (51, '2.01.17', 'Western Lowlands', 'WES-LOW', 'goat', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (52, '2.01.18', 'Widar', 'WID', 'goat', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (53, '2.01.19', 'Woyito Guji', NULL, 'goat', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (54, '2.02.01', 'Anglo-Nubian', 'ANG-N', 'goat', 'Exotic', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (55, '2.02.02', 'Toggenburg', 'TOG', 'goat', 'Exotic', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (56, '2.03.02.01-01.10', 'Anglo-Nubian x Hararghe Highland', 'ANG-N-HAR-HIG', 'goat', 'Cross', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (57, '2.03.02.01-01.13', 'Anglo-Nubian x Long eared Somali', 'ANG-N-LON-EAR-SOM', 'goat', 'Cross', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (58, '2.03.02.02-01.10', 'Toggenburg x Hararghe Highland', 'TOG-HAR-HIG', 'goat', 'Cross', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (59, '3.01.01', 'Abergele', 'ABEs', 'sheep', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (60, '3.01.02', 'Afar', 'AFAs', 'sheep', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (61, '3.01.03', 'Arsi', 'ARSs', 'sheep', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (62, '3.01.04', 'Begayit', 'BEGs', 'sheep', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (63, '3.01.05', 'Begi-Degu', 'BEG-DEG', 'sheep', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (64, '3.01.06', 'Black Head Somali', 'BLA-HEA-SOM', 'sheep', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (65, '3.01.07', 'Bonga', 'BON', 'sheep', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (66, '3.01.08', 'Dangila', 'DAN', 'sheep', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (67, '3.01.09', 'Farta', 'FAR', 'sheep', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (68, '3.01.10', 'Horro', 'HORs', 'sheep', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (69, '3.01.11', 'Ille', 'ILLs', 'sheep', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (70, '3.01.12', 'Menz', 'MEN', 'sheep', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (71, '3.01.13', 'Tukur', 'TUK', 'sheep', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (72, '3.02.01', 'Awassi', 'AWA', 'sheep', 'Exotic', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (73, '3.02.02', 'Bleu du Maine', 'BLE-DU-MAI', 'sheep', 'Exotic', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (74, '3.02.03', 'Corriedale', 'COR', 'sheep', 'Exotic', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (75, '3.02.04', 'Dorper', 'DOR', 'sheep', 'Exotic', TRUE, TRUE, 'National Livestock Data Standard (MOA, 2024)'),
  (76, '3.02.05', 'Hampshire', 'HAMs', 'sheep', 'Exotic', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (77, '3.02.06', 'Merino', 'MER', 'sheep', 'Exotic', TRUE, TRUE, 'National Livestock Data Standard (MOA, 2024)'),
  (78, '3.02.07', 'Romney', 'ROM', 'sheep', 'Exotic', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (79, '3.03.02.01-01.12', 'Awassi x Menz', 'AWA-MEN', 'sheep', 'Cross', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (80, '3.03.02.02-01.12', 'Bleu du Maine x Menz', 'BLE-DU-MAI-MEN', 'sheep', 'Cross', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (81, '3.03.02.04-01.12', 'Dorper x Menz', 'DOR-MEN', 'sheep', 'Cross', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (82, '3.03.02.05-01.12', 'Hampshire x Menz', 'HAM-MEN', 'sheep', 'Cross', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (83, '3.03.02.07-01.12', 'Romney x Menz', 'ROM-MEN', 'sheep', 'Cross', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (84, '4.01.01', 'Amibara', 'AMI', 'camel', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (85, '4.01.02', 'Gelleb', 'GEL', 'camel', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (86, '4.01.03', 'Hoor', 'HOO', 'camel', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (87, '4.01.04', 'Jijiga', 'JIJc', 'camel', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (88, '4.01.05', 'Liben', 'LIB', 'camel', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (89, '4.01.06', 'Mille', 'MIL', 'camel', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (90, '4.01.07', 'Shinille', 'SHI', 'camel', 'Indigenous', TRUE, FALSE, 'National Livestock Data Standard (MOA, 2024)'),
  (91, NULL, 'Boer', NULL, 'goat', 'Exotic', FALSE, TRUE, 'ET-LITS registry'),
  (92, NULL, 'Gir', NULL, 'cattle', 'Exotic', FALSE, TRUE, 'ET-LITS registry'),
  (93, NULL, 'Ethiopian Camel', NULL, 'camel', 'Indigenous', FALSE, TRUE, 'ET-LITS registry'),
  (94, NULL, 'Honey Bee', NULL, 'beehive', 'Indigenous', FALSE, TRUE, 'ET-LITS registry')
) AS source (id, breed_code, name, abbreviation, source_species_code, breed_type, in_national_standard, in_etlits_registry, source_name)
JOIN g2p_livestock_type species
  ON species.species_code = source.source_species_code
ON CONFLICT (id) DO UPDATE SET
    breed_code = EXCLUDED.breed_code,
    name = EXCLUDED.name,
    abbreviation = EXCLUDED.abbreviation,
    species_id = EXCLUDED.species_id,
    breed_type = EXCLUDED.breed_type,
    in_national_standard = EXCLUDED.in_national_standard,
    in_etlits_registry = EXCLUDED.in_etlits_registry,
    source = EXCLUDED.source;

INSERT INTO g2p_livestock_gender (code, name, description, in_etlits_registry) VALUES
  ('Female', 'Female', 'An individual of the sex that has ovaries and produces ova.', TRUE),
  ('FemaleNeuter', 'Female neuter', 'Female animal whose reproductive organs have been removed so that it cannot reproduce.', FALSE),
  ('Male', 'Male', 'An individual of the gamete-producing sex that fertilises the female.', TRUE),
  ('MaleNeuter', 'Male neuter', 'Male animal whose testicles have been rendered dysfunctional through an approved procedure.', FALSE)
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    in_etlits_registry = EXCLUDED.in_etlits_registry;

INSERT INTO g2p_livestock_location_type (code, name, ethiopian_zone_name, altitude_description, ecological_zone_id, description) VALUES
  ('High Land', 'High land', 'Dega', 'Highland zone, typically above 2,300 m', 3, 'Cool highland grazing areas.'),
  ('Low Land', 'Low land', 'Kolla', 'Lowland zone, typically below 1,500 m', 1, 'Hot lowland and pastoral grazing areas.'),
  ('Mid Land', 'Mid land', 'Weyna Dega', 'Mid-altitude zone, typically 1,500-2,300 m', 2, 'Mid-altitude mixed crop and livestock areas.')
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    ethiopian_zone_name = EXCLUDED.ethiopian_zone_name,
    altitude_description = EXCLUDED.altitude_description,
    ecological_zone_id = EXCLUDED.ecological_zone_id,
    description = EXCLUDED.description;

INSERT INTO g2p_livestock_body_condition (code, bcs_score, condition_label, fatness_label, etlits_label, description) VALUES
  ('BCS1', 1, 'Poor', 'Very Thin', NULL, 'Spinous and transverse processes prominent and sharp, no fat cover over the eye muscle.'),
  ('BCS2', 2, 'Fair', 'Thin', 'Thin', 'Spinous process prominent but smooth, eye muscle area of moderate depth with little fat cover.'),
  ('BCS3', 3, 'Good', 'Moderate', 'Moderate Weight', 'Spinous process a small smooth elevation, eye muscle area full with a moderate degree of fat cover.'),
  ('BCS4', 4, 'Very Good', 'Fat', 'Fat', 'Spinous processes detected only under pressure, eye muscle area full with a thick fat covering.'),
  ('BCS5', 5, 'Excellent', 'Very Fat', NULL, 'Transverse process ends cannot be felt, eye muscle area full with a very thick fat covering.')
ON CONFLICT (code) DO UPDATE SET
    bcs_score = EXCLUDED.bcs_score,
    condition_label = EXCLUDED.condition_label,
    fatness_label = EXCLUDED.fatness_label,
    etlits_label = EXCLUDED.etlits_label,
    description = EXCLUDED.description;

INSERT INTO g2p_livestock_production_type (code, name, standard_purpose, in_national_standard, in_etlits_registry, description) VALUES
  ('Breeding', 'Breeding', NULL, FALSE, TRUE, 'Animal kept to produce offspring.'),
  ('Castrated', 'Castrated', NULL, FALSE, TRUE, 'Recorded by ET-LITS as a production type; the national standard treats neutering as a sex enumerator (MaleNeuter) rather than a production purpose.'),
  ('Draft Power', 'Draft power', 'Draft power', TRUE, FALSE, 'Animal used to draw ploughs or carts.'),
  ('Dual Purpose', 'Dual purpose', NULL, FALSE, TRUE, 'Animal kept for two purposes, typically milk and meat.'),
  ('Dung', 'Dung', 'Dung', TRUE, FALSE, 'Animal kept partly for dung used as fuel or fertiliser.'),
  ('Egg', 'Egg', NULL, FALSE, TRUE, 'Poultry kept for egg production; no catalogued species carries this purpose.'),
  ('Hide/Skin', 'Hide or skin', 'Hide/Skin', TRUE, FALSE, 'Animal kept for hides and skins.'),
  ('Honey', 'Honey', NULL, FALSE, TRUE, 'Bee colony kept for honey production.'),
  ('Meat', 'Meat', 'Meat', TRUE, TRUE, 'Animal kept for meat production.'),
  ('Milk', 'Milk', 'Milk', TRUE, TRUE, 'Animal kept for milk production.'),
  ('Other (social status)', 'Other (social status)', 'Other (social status)', TRUE, FALSE, 'Animal kept for social or cultural value.'),
  ('Pack Animal', 'Pack animal', 'Draft power', FALSE, TRUE, 'ET-LITS label for animals used to carry loads; equivalent to the standard draft power purpose.'),
  ('Wool', 'Wool', 'Wool', TRUE, FALSE, 'Sheep kept for wool production.')
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    standard_purpose = EXCLUDED.standard_purpose,
    in_national_standard = EXCLUDED.in_national_standard,
    in_etlits_registry = EXCLUDED.in_etlits_registry,
    description = EXCLUDED.description;

INSERT INTO g2p_livestock_record_status (code, name, sort_order, is_live_master_data, description) VALUES
  ('PENDING', 'Pending', 1, FALSE, 'Submitted and awaiting review.'),
  ('REWORK', 'Rework', 2, FALSE, 'Returned to the submitter for correction.'),
  ('REJECTED', 'Rejected', 3, FALSE, 'Reviewed and rejected.'),
  ('APPROVED', 'Approved', 4, FALSE, 'Approved by a reviewer but not yet live.'),
  ('ACTIVE', 'Active', 5, TRUE, 'Approved and live in the registry.'),
  ('INACTIVE', 'Inactive', 6, FALSE, 'Previously live and since retired.')
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    sort_order = EXCLUDED.sort_order,
    is_live_master_data = EXCLUDED.is_live_master_data,
    description = EXCLUDED.description;

INSERT INTO g2p_livestock_production_type_species
  (production_type_code, species_id)
SELECT source.production_type_code, species.id
FROM (VALUES
  ('Breeding', 'camel'),
  ('Breeding', 'cattle'),
  ('Breeding', 'goat'),
  ('Breeding', 'sheep'),
  ('Castrated', 'camel'),
  ('Castrated', 'cattle'),
  ('Castrated', 'goat'),
  ('Castrated', 'sheep'),
  ('Draft Power', 'camel'),
  ('Draft Power', 'cattle'),
  ('Dual Purpose', 'camel'),
  ('Dual Purpose', 'cattle'),
  ('Dual Purpose', 'goat'),
  ('Dual Purpose', 'sheep'),
  ('Dung', 'camel'),
  ('Dung', 'cattle'),
  ('Hide/Skin', 'cattle'),
  ('Hide/Skin', 'goat'),
  ('Hide/Skin', 'sheep'),
  ('Honey', 'beehive'),
  ('Meat', 'camel'),
  ('Meat', 'cattle'),
  ('Meat', 'goat'),
  ('Meat', 'sheep'),
  ('Milk', 'camel'),
  ('Milk', 'cattle'),
  ('Milk', 'goat'),
  ('Other (social status)', 'camel'),
  ('Other (social status)', 'cattle'),
  ('Other (social status)', 'goat'),
  ('Other (social status)', 'sheep'),
  ('Pack Animal', 'camel'),
  ('Pack Animal', 'cattle'),
  ('Wool', 'sheep')
) AS source (production_type_code, source_species_code)
JOIN g2p_livestock_type species
  ON species.species_code = source.source_species_code
ON CONFLICT (production_type_code, species_id) DO NOTHING;

INSERT INTO g2p_livestock_registry_entry (id, species_code, breed_name, breed_id, gender_code, location_type_code, body_condition_code, production_type_code, status, created_on, updated_on) VALUES
  ('livestock-008569662215', 'cattle', 'Boran', 10, 'Female', 'Low Land', 'BCS3', 'Milk', 'ACTIVE', '2026-08-10T11:28:32.902Z', '2026-08-13T07:49:28.294Z'),
  ('livestock-019210037813', 'camel', 'Boran', 10, 'Female', 'High Land', 'BCS3', 'Meat', 'ACTIVE', '2026-08-13T07:45:05.823Z', '2026-08-13T13:14:19.920Z'),
  ('livestock-198953821362', 'cattle', 'Gir', 92, 'Female', 'Mid Land', 'BCS4', 'Milk', 'INACTIVE', '2026-08-14T10:49:56.648Z', '2026-08-14T10:57:35.640Z'),
  ('livestock-212708917710', 'sheep', 'Merino', 77, 'Female', 'High Land', 'BCS2', 'Dual Purpose', 'REJECTED', '2026-08-13T13:07:45.825Z', '2026-08-13T13:15:14.941Z'),
  ('livestock-293287324110', 'cattle', 'BoranR', NULL, 'Male', 'High Land', 'BCS2', 'Castrated', 'APPROVED', '2026-08-14T11:01:14.745Z', '2026-08-14T11:04:03.489Z'),
  ('livestock-350410916860', 'beehive', 'Honey Bee', 94, 'Female', 'Mid Land', 'BCS3', 'Honey', 'PENDING', '2026-08-13T11:05:00.816Z', '2026-08-13T11:05:00.816Z'),
  ('livestock-414930215931', 'goat', 'Boer', 91, 'Female', 'Mid Land', 'BCS3', 'Pack Animal', 'INACTIVE', '2026-08-13T13:19:52.800Z', '2026-08-14T07:40:16.213Z'),
  ('livestock-469557638335', 'cattle', 'Test', NULL, 'Male', 'High Land', 'BCS4', 'Meat', 'PENDING', '2026-08-13T07:46:14.127Z', '2026-08-13T07:46:14.127Z'),
  ('livestock-479102083675', 'sheep', 'Dorper', 75, 'Male', 'Mid Land', 'BCS3', 'Breeding', 'PENDING', '2026-08-13T12:42:19.245Z', '2026-08-13T12:42:19.245Z'),
  ('livestock-738602771660', 'camel', 'Ethiopian Camel', 93, 'Female', 'Mid Land', 'BCS3', 'Pack Animal', 'REWORK', '2026-08-14T08:04:25.847Z', '2026-08-14T08:09:55.398Z'),
  ('livestock-758330957676', 'goat', 'Boer', 91, 'Female', 'Mid Land', 'BCS3', 'Pack Animal', 'REWORK', '2026-08-13T13:14:52.014Z', '2026-08-13T13:15:50.246Z'),
  ('livestock-918889998727', 'cattle', 'Holstein Friesian', 26, 'Male', 'Mid Land', 'BCS2', 'Egg', 'REWORK', '2026-08-13T07:56:55.101Z', '2026-08-13T07:59:36.932Z')
ON CONFLICT (id) DO UPDATE SET
    species_code = EXCLUDED.species_code,
    breed_name = EXCLUDED.breed_name,
    breed_id = EXCLUDED.breed_id,
    gender_code = EXCLUDED.gender_code,
    location_type_code = EXCLUDED.location_type_code,
    body_condition_code = EXCLUDED.body_condition_code,
    production_type_code = EXCLUDED.production_type_code,
    status = EXCLUDED.status,
    created_on = EXCLUDED.created_on,
    updated_on = EXCLUDED.updated_on;
