presets_abc = {
    "Default-abc": {
        "filepath": "",
        "selected": False,
        "flatten": False,
        "collection": "",
        "start": -2147483648,
        "end": -2147483648,
        "xsamples": 1,
        "gsamples": 1,
        "sh_open": 0.0,
        "sh_close": 1.0,
        "uvs": True,
        "packuv": True,
        "normals": True,
        "vcolors": False,
        "orcos": True,
        "face_sets": False,
        "subdiv_schema": False,
        "apply_subdiv": False,
        "curves_as_mesh": False,
        "use_instancing": True,
        "global_scale": 1.0,
        "triangulate": False,
        "quad_method": "SHORTEST_DIAGONAL",
        "ngon_method": "BEAUTY",
        "export_hair": True,
        "export_particles": True,
        "as_background_job": False,
        "evaluation_mode": "RENDER",
        # Kept last: newer Alembic-exporter options not confirmed present on every
        # supported Blender version (live-verified on 5.2 only). Blender's native
        # preset loader (script.execute_preset) execs this file top to bottom and
        # aborts on the first unknown property, so keeping these at the end means
        # every earlier property still gets applied on older Blender versions
        # instead of being skipped.
        "export_custom_properties": True,
        "init_scene_frame_range": True,
    },
}
