import hybridLogger
import time
import testingLeds
    

def runMain():
    with hybridLogger.HybridLogger("Amplifier") as logger:
        try:
            logger.info("Amplifier script started")


            testingLeds.test()
                
        except KeyboardInterrupt:
            logger.info("Received shutdown signal (Ctrl+C)")
            logger.info("Shutting down gracefully...")
            
        finally:
            logger.info("Amplifier script stopped")


if __name__ == "__main__":
    runMain()

