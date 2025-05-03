#!/usr/bin/env python3
"""
Top-level script to execute the complete London transport graph build pipeline.

This script imports and runs the build_graph function from the
networkx_graph.create_graph package, which handles all the necessary steps
to generate the final weighted hub graph.

Can be run either:
1. As a module from the PROJECT ROOT directory:
   python3 -m networkx_graph.build_graph
2. Directly from the PROJECT ROOT directory:
   python3 networkx_graph/build_graph.py
"""

import sys
import os
import logging

# --- Path Setup --- 
# If run directly, add the project root (parent directory) to sys.path
# so the absolute import 'from networkx_graph...' works.
if __name__ == "__main__" and __package__ is None:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
    if PROJECT_ROOT not in sys.path:
        sys.path.insert(0, PROJECT_ROOT)
# --- End Path Setup ---

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Attempt to import the build function using absolute path
try:
    from networkx_graph.create_graph import build_graph
except ImportError as e:
    logging.error(f"Failed to import build_graph function: {e}")
    logging.error("Ensure all dependencies are installed.")
    logging.error("Try running either:")
    logging.error("  python3 -m networkx_graph.build_graph")
    logging.error("  python3 networkx_graph/build_graph.py")
    sys.exit(1)
except Exception as e:
    logging.error(f"An unexpected error occurred during import: {e}")
    sys.exit(1)

def main():
    """Runs the graph building pipeline."""
    logging.info("Starting the main graph build process...")
    try:
        build_graph() # Call the main pipeline function
        logging.info("Graph build process completed successfully.")
    except ImportError:
        # Error already logged during import
        logging.error("Exiting due to import errors.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An error occurred during the graph build process: {e}", exc_info=True)
        logging.error("Exiting due to pipeline failure.")
        sys.exit(1)

if __name__ == "__main__":
    main() 