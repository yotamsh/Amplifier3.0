import hybridLogger


def runMain():
    logger = hybridLogger.setup_logger("Amplifier")

    logger.info("the script started")
    logger.debug("debug details")
    logger.error("something went wrong")

if __name__ == "__main__":
    runMain()

    