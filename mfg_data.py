# mfg_data.py

Y_TZP_DENTAL_DATA = {
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
}
