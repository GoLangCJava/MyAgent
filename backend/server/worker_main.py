import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../package"))

from deep_platform.services.run_worker import WorkerSettings

def main():
    import logging.config
    from arq.logs import default_log_config
    from arq.worker import run_worker
    logging.config.dictConfig(default_log_config(False))
    run_worker(WorkerSettings)

if __name__=="__main__":
    main()
