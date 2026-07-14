class ProviderRegistry:
    """
    Registry yang bertugas menyimpan dan
    menyediakan akses ke seluruh AI Provider
    yang telah diregistrasi.
    """

    def __init__(self):

        self.providers = {}

    def register(
        self,
        name: str,
        provider,
    ):

        self.providers[name] = provider

    def unregister(
        self,
        name: str,
    ):

        self.providers.pop(name, None)

    def get(
        self,
        name: str,
    ):

        if name not in self.providers:
            raise ValueError(
                f"Provider '{name}' tidak terdaftar."
            )

        return self.providers[name]

    def exists(
        self,
        name: str,
    ):

        return name in self.providers

    def list(
        self,
    ):

        """
        Return seluruh nama provider
        yang telah diregistrasi.
        """

        return tuple(
            self.providers.keys()
        )

    def all(
        self,
    ):

        """
        Return seluruh instance provider.
        """

        return tuple(
            self.providers.values()
        )

    def items(
        self,
    ):

        """
        Return pasangan
        (provider_name, provider).
        """

        return tuple(
            self.providers.items()
        )

    def clear(
        self,
    ):

        """
        Hapus seluruh provider yang
        telah diregistrasi.
        """

        self.providers.clear()