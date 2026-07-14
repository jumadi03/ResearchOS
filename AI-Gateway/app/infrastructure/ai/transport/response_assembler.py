class ResponseAssembler:
    """
    Converts provider payloads into
    canonical text responses.
    """

    @staticmethod
    def assemble(
        payload: dict,
    ) -> str:

        return payload.get(
            "response",
            "",
        )