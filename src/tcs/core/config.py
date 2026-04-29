class ConfigOperations:
    """
    Repository configuration commands.
    """

    SUPPORTED_CONFIG_KEYS = ("user.name", "user.email")

    def config(self, key: str, value: str) -> str:
        """
        Set a supported repository configuration value.
        """
        if key not in self.SUPPORTED_CONFIG_KEYS:
            raise ValueError("Unsupported config key. Use 'user.name' or 'user.email'.")

        config = self._load_config()
        config[key] = value
        self._save_config(config)
        return f"Set {key} to {value}"
