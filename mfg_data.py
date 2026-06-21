# mfg_data.py

MATERIALS_DB = {
    "Y-TZP Zirconia": {
        "material": "Y-TZP Zirconia (Yttria-Stabilized Tetragonal Zirconia Polycrystal)",
        "dental_applications": [
            "Single crowns",
            "Multi-unit bridges",
            "Abutments",
            "Dental implants"
        ],
        "baseline_mechanical_properties": {
            "fracture_toughness": {
                "value_range": [5.0, 10.0],
                "unit": "MPa·m^(1/2)",
                "method": "Indentation fracture / Single-edge V-notched beam (SEVNB)"
            },
            "flexural_strength": {
                "value_range": [900, 1200],
                "unit": "MPa",
                "method": "3-point or 4-point bending test"
            }
        },
        "toughness_additives": {
            "Alumina (Al2O3)": {
                "typical_concentration_range": "0.05 wt% - 0.25 wt%",
                "pros": [
                    "Significantly improves resistance to low-temperature degradation (hydrothermal aging)",
                    "Increases hardness and wear resistance",
                    "Enhances grain boundary strength, preventing grain pull-out"
                ],
                "cons": [
                    "Reduces translucency (critical for anterior dental restorations) due to refractive index mismatch",
                    "Can decrease fracture toughness if added in excess",
                    "Increases sintering temperature requirements"
                ]
            },
            "Ceria (CeO2)": {
                "typical_concentration_range": "8 mol% - 12 mol%",
                "pros": [
                    "Provides exceptional fracture toughness via stress-induced phase transformation",
                    "Excellent hydrothermal stability under oral conditions",
                    "Increases resistance to cyclic fatigue and chipping"
                ],
                "cons": [
                    "Reduces baseline hardness and flexural strength compared to alumina-doped Y-TZP",
                    "Alters optical characteristics, giving the ceramic a yellowish coloration",
                    "Lower aesthetic appeal, requiring extra veneering porcelain"
                ]
            }
        },
        "dlp_print_parameters": {
            "layer_thickness": {
                "range": [20, 50],
                "unit": "microns",
                "recommended": 30
            },
            "sintering_temperature_profile": {
                "stages": [
                    {
                        "stage_name": "Debinding (Organic Burnout)",
                        "ramp_rate": 0.5,
                        "ramp_rate_unit": "°C/min",
                        "target_temperature": 600,
                        "temperature_unit": "°C",
                        "dwell_time": 120,
                        "dwell_time_unit": "minutes",
                        "description": "Slow heating to release photocurable resin binders without causing bloating, delamination, or cracking."
                    },
                    {
                        "stage_name": "Sintering (Densification)",
                        "ramp_rate": 2.0,
                        "ramp_rate_unit": "°C/min",
                        "target_temperature": 1500,
                        "temperature_unit": "°C",
                        "dwell_time": 120,
                        "dwell_time_unit": "minutes",
                        "description": "High temperature dwell to promote solid-state diffusion and achieve full density of the tetragonal phase."
                    },
                    {
                        "stage_name": "Controlled Cooling",
                        "ramp_rate": -3.0,
                        "ramp_rate_unit": "°C/min",
                        "target_temperature": 100,
                        "temperature_unit": "°C",
                        "dwell_time": 0,
                        "dwell_time_unit": "minutes",
                        "description": "Controlled thermal ramp-down to prevent thermal shock and unwanted monoclinic phase transformation."
                    }
                ]
            }
        }
    },
    "Alumina Bioceramics": {
        "material": "Alumina Bioceramics (Alpha-Al2O3)",
        "dental_applications": [
            "Orthodontic brackets",
            "Dental implants (historical/experimental)",
            "Wear-resistant load-bearing coatings"
        ],
        "baseline_mechanical_properties": {
            "fracture_toughness": {
                "value_range": [3.0, 5.0],
                "unit": "MPa·m^(1/2)",
                "method": "Indentation fracture / Chevron notch"
            },
            "flexural_strength": {
                "value_range": [400, 600],
                "unit": "MPa",
                "method": "3-point bending test"
            }
        },
        "toughness_additives": {
            "Zirconia (ZrO2)": {
                "typical_concentration_range": "10 wt% - 20 wt% (ZTA)",
                "pros": [
                    "Significantly increases fracture toughness (transformation toughening)",
                    "Maintains high hardness of the alumina matrix",
                    "Improves thermal shock resistance"
                ],
                "cons": [
                    "Decreases baseline wear resistance slightly compared to pure alumina",
                    "Susceptible to hydrothermal aging (low-temperature degradation) of the zirconia phase",
                    "Requires careful control of phase distribution during sintering"
                ]
            }
        },
        "dlp_print_parameters": {
            "layer_thickness": {
                "range": [25, 60],
                "unit": "microns",
                "recommended": 40
            },
            "sintering_temperature_profile": {
                "stages": [
                    {
                        "stage_name": "Debinding (Organic Burnout)",
                        "ramp_rate": 0.4,
                        "ramp_rate_unit": "°C/min",
                        "target_temperature": 550,
                        "temperature_unit": "°C",
                        "dwell_time": 180,
                        "dwell_time_unit": "minutes",
                        "description": "Gentle heating to burn off photo-curable binder without structural cracking."
                    },
                    {
                        "stage_name": "Sintering (Densification)",
                        "ramp_rate": 3.0,
                        "ramp_rate_unit": "°C/min",
                        "target_temperature": 1600,
                        "temperature_unit": "°C",
                        "dwell_time": 120,
                        "dwell_time_unit": "minutes",
                        "description": "High temperature sintering to achieve grain coalescence and eliminate porosity in alpha-alumina."
                    },
                    {
                        "stage_name": "Controlled Cooling",
                        "ramp_rate": -4.0,
                        "ramp_rate_unit": "°C/min",
                        "target_temperature": 100,
                        "temperature_unit": "°C",
                        "dwell_time": 0,
                        "dwell_time_unit": "minutes",
                        "description": "Controlled ramp-down to manage thermal gradients and internal residual stresses."
                    }
                ]
            }
        }
    },
    "316L Stainless Steel": {
        "material": "316L Stainless Steel (UNS S31603)",
        "dental_applications": [
            "Orthodontic wires",
            "Temporary anchorage devices (TADs)",
            "Dental instrument brackets"
        ],
        "baseline_mechanical_properties": {
            "fracture_toughness": {
                "value_range": [50.0, 100.0],
                "unit": "MPa·m^(1/2)",
                "method": "Elastic-plastic J-integral test"
            },
            "flexural_strength": {
                "value_range": [480, 680],
                "unit": "MPa",
                "method": "Tensile / flexural yield tests"
            }
        },
        "toughness_additives": {
            "Nickel (Ni)": {
                "typical_concentration_range": "10.0 wt% - 14.0 wt%",
                "pros": [
                    "Stabilizes the face-centered cubic (FCC) austenitic phase",
                    "Provides high ductility and impact toughness",
                    "Enhances overall corrosion resistance"
                ],
                "cons": [
                    "Can trigger nickel allergic reactions in sensitive patients",
                    "Increases material cost",
                    "Slightly reduces surface hardness compared to ferritic steels"
                ]
            }
        },
        "dlp_print_parameters": {
            "layer_thickness": {
                "range": [30, 75],
                "unit": "microns",
                "recommended": 50
            },
            "sintering_temperature_profile": {
                "stages": [
                    {
                        "stage_name": "Debinding (Organic Burnout)",
                        "ramp_rate": 1.0,
                        "ramp_rate_unit": "°C/min",
                        "target_temperature": 500,
                        "temperature_unit": "°C",
                        "dwell_time": 60,
                        "dwell_time_unit": "minutes",
                        "description": "Burnout of binders under hydrogen or vacuum to prevent carbon/oxygen contamination."
                    },
                    {
                        "stage_name": "Sintering (Densification)",
                        "ramp_rate": 5.0,
                        "ramp_rate_unit": "°C/min",
                        "target_temperature": 1360,
                        "temperature_unit": "°C",
                        "dwell_time": 60,
                        "dwell_time_unit": "minutes",
                        "description": "High temperature sintering under high vacuum or dry hydrogen shield to prevent oxidation."
                    },
                    {
                        "stage_name": "Controlled Cooling",
                        "ramp_rate": -10.0,
                        "ramp_rate_unit": "°C/min",
                        "target_temperature": 100,
                        "temperature_unit": "°C",
                        "dwell_time": 0,
                        "dwell_time_unit": "minutes",
                        "description": "Rapid cooling under inert gas shield to avoid chromium carbide precipitation at grain boundaries."
                    }
                ]
            }
        }
    }
}

# Keep original variable pointing to Zirconia for backwards compatibility
Y_TZP_DENTAL_DATA = MATERIALS_DB["Y-TZP Zirconia"]
