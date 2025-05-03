"""
Package for creating the London transport network graph.

This package contains modules executed sequentially to build the hub-based graph, 
calculate transfer links and weights, fetch timetable data, calculate line edge 
weights from timetables or the Journey API, and finally combine everything into 
a fully weighted graph.
"""

import logging
import os
import io # Added for log capture

# Set up logging for the package
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define relative paths used by the final step within this package context
# These paths are relative to the create_graph directory
_FINAL_GRAPH_INPUT_PATH = 'output/stage3_networkx_graph_hubs_with_transfer_weights.json'
_WEIGHTS_INPUT_PATH = 'output/stage4_calculated_hub_edge_weights.json'
_FINAL_GRAPH_OUTPUT_PATH = 'output/final_networkx_graph.json'


# Import main functions from each step module
# It's generally better practice to have clear main functions, 
# but we use the names identified from `if __name__ == "__main__":` blocks.
try:
    from .build_hub_graph import build_base_hub_graph
    from .add_proximity_transfers import add_proximity_transfers
    from .calculate_transfer_weights import calculate_transfer_weights
    # Renaming main functions for clarity where needed
    from .get_timetable_data import main as fetch_timetable_data
    from .get_tube_dlr_edge_weights import main as calculate_tube_dlr_weights
    from .get_overground_Elizabeth_edge_weights import main as calculate_og_el_weights
    from .update_graph_weights import update_graph_edge_weights
    from .validate_graph_weights import main as validate_graph_weights # Added validation import
except ImportError as e:
    logging.error(f"Failed to import a graph creation step: {e}")
    # Depending on desired behavior, you might want to raise the error
    # raise ImportError(f"Could not import necessary graph creation modules: {e}") from e
    # Or define a dummy build_graph function to indicate failure
    def build_graph():
        logging.error("Graph building unavailable due to import errors.")
        raise ImportError("Could not import necessary graph creation modules.")

def build_graph():
    """
    Executes the full pipeline to build the weighted London transport hub graph.
    
    Runs the following steps in sequence:
    1. Build base hub graph.
    2. Add proximity transfers.
    3. Calculate transfer weights.
    4. Fetch timetable data.
    5. Calculate Tube/DLR line weights from timetable data.
    6. Calculate Overground/Elizabeth line weights using Journey API.
    6.5. Validate calculated weights against the graph structure.
    7. Update graph with all calculated line weights.
    """
    try:
        logging.info("--- Starting Graph Build Pipeline ---")

        print("\n Grab a cuppa, this will take a while...\n")

        logging.info("Step 1: Building base hub graph...")
        build_base_hub_graph()
        logging.info("Step 1: Completed.")

        logging.info("Step 2: Adding proximity transfers...")
        add_proximity_transfers()
        logging.info("Step 2: Completed.")

        logging.info("Step 3: Calculating transfer weights...")
        calculate_transfer_weights()
        logging.info("Step 3: Completed.")

        logging.info("Step 4: Fetching timetable data...")
        fetch_timetable_data()
        logging.info("Step 4: Completed.")

        logging.info("Step 5: Calculating Tube/DLR line weights...")
        calculate_tube_dlr_weights()
        logging.info("Step 5: Completed.")

        logging.info("Step 6: Calculating Overground/Elizabeth line weights...")
        calculate_og_el_weights()
        logging.info("Step 6: Completed.")

        logging.info("Step 6.5: Validating calculated graph weights...")
        log_capture_string = io.StringIO()
        ch = logging.StreamHandler(log_capture_string)
        ch.setLevel(logging.WARNING) # Capture WARNING and ERROR
        # Optional: Add a formatter if you want specific formatting in the captured log
        # formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
        # ch.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.addHandler(ch)
        validation_passed = True

        try:
            validate_graph_weights() # Run the validation function
            # Check captured logs AFTER the function finishes
            log_contents = log_capture_string.getvalue()
            if "WARNING" in log_contents or "ERROR" in log_contents:
                validation_passed = False
                logging.error("--- Validation Failed ---")
                logging.error("Validation script output indicates potential issues (check WARNING/ERROR messages):")
                # Log the captured warnings/errors to the main log stream for visibility
                for line in log_contents.strip().split('\n'):
                    logging.error(f"Validation Log: {line}")
                logging.error("--- End Validation Output ---")
        except Exception as validation_exc:
             logging.error(f"Validation script itself raised an exception: {validation_exc}", exc_info=True)
             validation_passed = False
        finally:
            # Ensure the handler is removed and buffer is closed
            root_logger.removeHandler(ch)
            log_capture_string.close()

        # Raise exception if validation failed
        if not validation_passed:
            raise ValueError("Graph weight validation failed. Check logs above for details.")
        else:
             logging.info("Step 6.5: Validation successful.")

        logging.info("Step 7: Updating graph with line weights...")
        # Ensure the output directory exists for the final output file
        os.makedirs(os.path.dirname(_FINAL_GRAPH_OUTPUT_PATH), exist_ok=True)
        update_graph_edge_weights(
            _FINAL_GRAPH_INPUT_PATH, 
            _WEIGHTS_INPUT_PATH, 
            _FINAL_GRAPH_OUTPUT_PATH
        )
        logging.info("Step 7: Completed.")

        logging.info("--- Graph Build Pipeline Finished Successfully ---")
        logging.info(f"Final weighted graph saved to: {_FINAL_GRAPH_OUTPUT_PATH}")

    except Exception as e:
        logging.error(f"Graph build pipeline failed: {e}", exc_info=True)
        # Re-raise the exception to signal failure to the caller
        raise

# Allow calling the build function directly if needed (e.g., for testing)
# Note: Running this file directly might have issues with relative imports 
# if not executed as part of the package.
# if __name__ == "__main__":
#     build_graph() 