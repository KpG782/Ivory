from services.catalog import SERVICES, detect_service


def test_detect_service_by_keyword():
    assert detect_service("i need a cleaning") == "cleaning"
    assert detect_service("my tooth is killing me") == "emergency"
    assert detect_service("teeth whitening please") == "whitening"
    assert detect_service("just a checkup consult") == "consultation"


def test_detect_service_checkup_only_is_cleaning():
    """Bare checkup without consult keywords resolves to cleaning."""
    assert detect_service("book me a checkup") == "cleaning"


def test_detect_service_none_for_unrelated():
    assert detect_service("what are your hours?") is None


def test_catalog_has_four_services():
    assert set(SERVICES) == {"cleaning", "consultation", "whitening", "emergency"}


def test_emergency_wins_when_cooccurring():
    """Emergency is checked first, so it wins even when cosmetic keywords co-occur."""
    assert detect_service("chipped tooth whitening") == "emergency"
    assert detect_service("toothache after a cleaning") == "emergency"


def test_consulting_is_not_consultation():
    """Word-boundary matching prevents 'consult' from matching 'consulting'."""
    assert detect_service("I work at a consulting firm") is None
