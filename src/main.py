import hybridLogger
import time
import logging
from tests import testingLeds
    

def runMain():
    main_logger = hybridLogger.HybridLogger("Amplifier")
    logger = main_logger.get_main_logger(logging.INFO)  # Convenience method
    
    try:
        logger.info("Amplifier script started")

        testingLeds.test()
            
    except KeyboardInterrupt:
        logger.info("Received shutdown signal (Ctrl+C)")
        logger.info("Shutting down gracefully...")
        
    finally:
        logger.info("Amplifier script stopped")
        main_logger.cleanup()


if __name__ == "__main__":
    runMain()

