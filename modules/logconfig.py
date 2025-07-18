"""
logconfig.py - updated 2025-07-17

Configures a global logger with a simple format.

Parameters:
- level: Logging level (e.g., logging.DEBUG, logging.INFO)
"""

import logging

class LggWrapper:
    def __init__(self, logger):
        self.em = logger.critical     # EMERGENCY (mapped to CRITICAL)
        self.a  = logger.critical     # ALERT     (same as critical)
        self.c  = logger.critical     # CRITICAL
        self.er = logger.error        # ERROR
        self.w  = logger.warning      # WARNING
        self.n  = logger.info         # NOTICE (mapped to INFO)
        self.i  = logger.info         # INFO
        self.d  = logger.debug        # DEBUG

def setup_logger(level=logging.INFO) -> LggWrapper:
    logging.basicConfig(
        level=level,
        format='[%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler()]
    )
    return LggWrapper(logging.getLogger())