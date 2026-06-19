import pandas as pd
import os
import logging

logger = logging.getLogger("pipeline")

class DataLoader:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir

    def load_claims(self, filename="claims.csv") -> pd.DataFrame:
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            logger.error(f"Claims file not found at {path}")
            return pd.DataFrame()
        logger.info(f"Loaded claims from {path}")
        return pd.read_csv(path)

    def load_user_history(self, filename="user_history.csv") -> pd.DataFrame:
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            logger.error(f"User history file not found at {path}")
            return pd.DataFrame()
        logger.info(f"Loaded user history from {path}")
        df = pd.read_csv(path)
        # Set user_id as index for rapid lookups
        if "user_id" in df.columns:
            df.set_index("user_id", inplace=True)
        return df

    def load_evidence_requirements(self, filename="evidence_requirements.csv") -> pd.DataFrame:
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            logger.error(f"Evidence requirements file not found at {path}")
            return pd.DataFrame()
        logger.info(f"Loaded evidence requirements from {path}")
        return pd.read_csv(path)

    def load_sample_claims(self, filename="sample_claims.csv") -> pd.DataFrame:
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            logger.error(f"Sample claims file not found at {path}")
            return pd.DataFrame()
        logger.info(f"Loaded sample claims from {path}")
        return pd.read_csv(path)
