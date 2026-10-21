from app.decision import decide, Det


def test_spray_when_clean_tea():
    assert decide([Det("tea_plant", 0.91)])[0] == "SPRAY"


def test_person_stops_spray():
    assert decide([Det("tea_plant", 0.95), Det("person", 0.45)])[0] == "NO_SPRAY"


def test_low_person_is_uncertain():
    assert decide([Det("tea_plant", 0.95), Det("person", 0.20)])[0] == "UNCERTAIN"


def test_animal_stops_spray():
    assert decide([Det("tea_plant", 0.95), Det("animal", 0.5)])[0] == "NO_SPRAY"


def test_road_stops_spray():
    assert decide([Det("tea_plant", 0.95), Det("road", 0.8)])[0] == "NO_SPRAY"


def test_low_tea_is_uncertain():
    assert decide([Det("tea_plant", 0.6)])[0] == "UNCERTAIN"


def test_no_tea_no_spray():
    assert decide([])[0] == "NO_SPRAY"


def test_geofence_blocks_spray():
    assert decide([Det("tea_plant", 0.95)], geofence_ok=False)[0] == "NO_SPRAY"


def test_poor_image_is_uncertain():
    assert decide([Det("tea_plant", 0.95)], image_ok=False)[0] == "UNCERTAIN"


def test_person_overrides_everything():
    dets = [Det("tea_plant", 0.99), Det("person", 0.31)]
    assert decide(dets)[0] == "NO_SPRAY"