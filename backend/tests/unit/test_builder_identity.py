from app.services.builder_service import builder_registry


def test_registered_test_builders_authorized():
    keypair = builder_registry.get_test_keypair("builder-A")
    assert keypair is not None
    _, pubkey_hex = keypair

    assert builder_registry.is_authorized("builder-A", pubkey_hex) is True


def test_unregistered_builder_unauthorized():
    assert builder_registry.is_authorized("builder-UNKNOWN", "a" * 64) is False


def test_registered_builder_with_wrong_pubkey_unauthorized():
    assert builder_registry.is_authorized("builder-A", "f" * 64) is False


def test_dynamic_builder_registration():
    builder_registry.register_builder("builder-custom", "c" * 64, "0x9999")
    assert builder_registry.is_authorized("builder-custom", "c" * 64) is True
    assert builder_registry.get_builder("builder-custom")["wallet_address"] == "0x9999"
