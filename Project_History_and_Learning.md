# Project History and Learning Log 

## 1. Purpose / Motivation

Before starting this project, I had no experience working with APIs or implementing specific algorithms on real-world datasets. I saw this as a crucial stepping stone in developing practical skills for the application of AI. The project allowed me to explore all of that while remaining technically challenging and personally relevant.

Rather than getting stuck on syntax, I focused on thinking like a systems designer: defining structure, testing logic, and ensuring that every step worked end-to-end. To support this, I used an LLM-assisted development environment - Cursor - throughout the process.

The sections below detail the project’s 6-week lifecycle including: development phases, what I learned from each stage, how my use of prompting evolved, what didn’t work, and the future directions I’m considering. All scripts related to each stage can be found in the `archive/` directory.

## 2. Key Changes & Design Decisions 

### 1. Replacing Live API Calls with a Structured Local Data Layer

My initial implementation relied on TfL’s StopPoint API for both validating user inputs and calculating journey times. I naively assumed this would scale, but quickly ran into performance issues:
- Over 1,700 "stations" returned for central London — including platforms, entrances, and other facilities
- Processing even 15 of these took 5+ minutes
- Journey time calculations were too slow for practical use

To solve this, I shifted toward building a local data cache. Initially, I used the StopPoint data, grouping stations using “Naptan IDs” to deduplicate facilities and entrances. I also added support for “connected stations” (e.g., the four different Stratford entries) so that validation and filtering could happen offline.

Later, I discovered a better TfL endpoint (`Line`) that provided a more unified and structured representation of the station network by returning a series of stations along a line (eg district line or DLR). The benefits included:
- Consistent station formatting
- Parent-child station relationships
- Logical deduplication while preserving full metadata
- Key pieces of data including: which modes of transport exist within a station and what lines exist within station.

This removed most of the noise and allowed the app to:
- Preload a clean, filtered dataset of ~466 usable stations
- Validate user input locally
- Make a single journey time API call per user during the final calculation phase

**What I Learned:**
- TfL’s data is rich but extremely messy — careful inspection and filtering are essential
- Grouping by Naptan ID and understanding TfL’s naming conventions is crucial for station-level logic
- Time spent reading API documentation properly up front would have saved a lot of refactoring

### 2. Updating Filtering Mechanics & Implementing graph

Even with a local station cache, the runtime was still too slow for practical use. I began implementing spatial heuristics to reduce the number of candidate stations used in the final API calls. After a few iterations, I settled on the following approach (still used today):

- **If more than two people:**  
  Filter stations to those within the convex hull of user start locations, then further restrict to those within a centroid-based circle covering ~70% of the group.

- **If two people:**  
  Use an elliptical region around the midpoint of their locations, then apply the same centroid-circle filter.

This reduced the number of candidate stations significantly and improved runtime, but was still not ready for practical use.

To address this, I built a `NetworkX` graph using data from the `Line` endpoint and the previous data structure:
- Each station became a **node**, with coordinates, transport modes, and line data stored as attributes
- **Edges** were added between consecutive stations along the same line, labeled by route
- **Transfer edges** were created between “connected” stations via the parent-child relationships found in the previous dataset (e.g., Stratford platforms)

This was the foundation for later implementing Dijkstra’s algorithm for optimal meeting point estimation.

**What I Learned:**
- Heuristic spatial filtering is a powerful performance tool, but it introduces tradeoffs: faster runtimes at the cost of possibly excluding valid options
- Tools like `NetworkX` simplify graph modeling immensely and are well-suited for multi-layered transport systems
- Designing your own graph structure helps clarify real-world constraints — e.g., transfer times, directional travel, and redundant station naming
- Good filtering logic is about **prioritization**, not just exclusion — especially when dealing with multiple users in complex networks

### 3. Validating Edge Weights & Implementing Dijkstra's Algorithm

Once the graph was fully connected and free of isolated nodes, I focused on validating and applying meaningful edge weights to support accurate route optimization. This involved extensive data cleaning, augmentation, and manual fallback strategies:

- **Tube and DLR lines:**
  - Most edge weights were retrieved using TfL’s `Timetable` API.
  - Gaps and inconsistencies from `Timetable` API were filled using direct `JourneyTime` API calls between affected stations.

- **Overground and Elizabeth Line:**
  - These modes lacked usable timetable data, so journey times were filled via direct `JourneyTime` API queries for every station pair connected by an edge.

- **Transfer edges:**
  - A fixed 5-minute penalty was applied to simulate walking time between platforms or lines within a station.

With edge weights applied, I implemented a custom version of Dijkstra’s algorithm. The key addition was a transfer penalty:
- If the current and previous edges belong to different lines **and** neither is marked as a `transfer`, an extra 5 minutes is added to simulate implicit transfer delays (e.g., cross-platform changes not captured by the `transfer` key).

This logic ensured more realistic journey estimations, especially in cases with complex, multi-line transfers.

**What I Learned:**
- Real-world transport data is often inconsistent, incomplete, or redundant; therefore it takes careful validation and creative fallbacks to build reliable models
- Building your own weighted graph forces you to think about **data granularity** and how different modes of transport introduce hidden edge cases (e.g., missing schedules, inconsistent naming)
- Customizing a standard algorithm (like Dijkstra) to reflect domain-specific constraints is a critical part of applied AI/system design
- Even "small" additions like implicit transfer penalties can significantly improve real-world accuracy and highlights how much abstraction standard graph models typically omit.

### 4. Transitioning to final structure

Despite implementing Dijkstra’s algorithm, we were still seeing incorrect or suboptimal paths. The final architectural change was converting the graph to a `MultiDiGraph`, which resolved several issues:

- **Multiple travel paths:** The previous graph collapsed multiple edges between stations, breaking line-specific routing. `MultiDiGraph` supports multiple edges between the same node pair.
- **Line awareness:** Without distinct edges for each line, our cross-line penalty logic couldn't apply accurately. The new structure preserved edge-level `line` attributes, allowing realistic transfer penalties.
- **Accurate network representation:** London's network often allows multiple travel options between the same stations — this structure models that accurately.

We also addressed issues with the parent-child station logic. Previously, each physical station was a node, which failed to capture station groups like the multiple stations within the Stratford complex. To fix this:

- We adopted TfL’s “Hub” model, where each **hub** became a graph node, and station-level details were stored as node attributes (used later for API requests).
- For better transfer logic, we queried the TfL API for all stations within 250 meters of each hub. If found, a `transfer` edge was added, with the edge weight set using the walking time from TfL’s `JourneyTime` API.

The final structure accurately models both routing logic and realistic transfer conditions across London's complex transport system. A full explanation of the graph creation process is available in the project `README`.

**What I Learned:**
- Pre-built libraries like `NetworkX` are powerful, but relying on them naively can introduce hidden inefficiencies or logic gaps. It's important to understand how they model data under the hood and to adapt their usage to the specific constraints of your problem.
- Using `MultiDiGraph` structures is essential when modeling real-world networks with multiple valid paths and edge-level metadata (e.g., lines, modes)
- Naive graph representations often break when multiple physical or logical structures are collapsed — fidelity in node/edge design directly affects pathfinding accuracy
- TfL’s internal “Hub” model is more semantically correct than treating each physical station as a node — modeling systems the way *they* do improves consistency and integration
- Transfer logic must reflect both **structural** transfers (e.g., connected platforms) and **spatial** transfers (e.g., stations within walking distance), and these require external validation (e.g., API, spatial lookups)
- Designing transport graphs forces you to think beyond algorithms — you’re modeling **physical systems**, not just abstract ones

## 3. Prompting & LLM use (Cursor Log)

I began development using Claude 3.7 (Sonnet), as its broad context window made it well-suited for reasoning across multiple files and assisting with high-level design planning. Early prompts were exploratory — focused on structuring logic, suggesting file layouts, and thinking through algorithmic strategies in natural language. All of this was aimed at supporting my learning, not shortcutting it.

As I became more comfortable with the problem space and with prompting itself, my use of LLMs shifted toward implementation support. I learned to write clear, directive prompts (often including pseudocode) that steered the model toward specific, context-aware outputs. At that point, I transitioned to Gemini 2.5 Pro, which I found more effective at generating clean, idiomatic Python in response to targeted instructions.

This shift from exploratory prompting to implementation support reflects a deeper lesson from the project: using LLMs effectively isn’t about offloading logic — it’s about guiding the model, critically evaluating its output, and adapting it to the realities of your system. However, the project also highlighted the **limitations** of current LLMs. While excellent at producing code when well-directed, they often struggle with large-scale structural problem-solving. For example, before I transitioned the graph to a `MultiDiGraph`, both models confidently insisted the original structure should work — despite clear flaws in edge logic. It took my own research and system-level reasoning to recognize that `MultiDiGraph` was the correct abstraction for modeling a transport network with multiple valid paths.

This reinforced a key insight: LLMs can accelerate development, but they still rely on the developer to define structure, validate correctness, and drive high-level problem-solving.

## 4. What Didn't Work / Dead Ends

### 4.1. Relying Too Heavily on API Calls
- **What Happened:** I initially assumed real-time API calls would be sufficient for both user input validation and journey calculations. In practice, this led to timeouts, inconsistent responses, and made iteration painfully slow.
- **What I Learned:** Real-time APIs are not a substitute for structured local data — especially when performance, repeatability, and debuggability are priorities.

### 4.2. Taking LLM Output at Face Value
- **What Happened:** On multiple occasions, Claude or Gemini confidently asserted that certain implementations would work, despite fundamental flaws. One key example: both models repeatedly insisted that a single-edge graph structure was compatible with our Dijkstra setup, when in reality it broke line-specific edge logic.
- **What I Learned:** LLMs often “hallucinate” correctness. They’re great at code generation when well-directed, but they lack true understanding of system-level logic. Critical evaluation and external research remain essential.

### 4.3. Fighting TfL’s Data Structure Instead of Using It
- **What Happened:** For much of the project, I tried to restructure TfL’s API data to fit my own mental model of the problem. This led to constant cleaning layers and mismatches across endpoints.
- **What I Learned:** Rather than forcing external data into a new format, it’s often better to model your system around the source data structure — especially when APIs are complex. Adopting TfL’s “Hub” concept as the basis for my node structure ultimately made the entire pipeline more consistent and maintainable.

### 4.4. Including Bus and Cycle Networks
- **What Happened**: Early in the project, I considered including bus and cycle infrastructure in the graph. However, both presented major challenges: bus routes are highly variable in timing and frequency, and integrating them accurately would require either live traffic data or a far more complex model. Cycle routing, while feasible, would have significantly increased data requirements and introduced entirely different constraints (e.g., street-level granularity, bike availability, user preferences).
- **What I Learned**: Not all features are worth implementing when the complexity outweighs their value within scope. Sometimes the best decision is to deliberately exclude certain systems to preserve clarity and focus. These networks could be explored in future iterations with more time and resources.

## 6. Conclusion

This project fundamentally reshaped how I think about building systems. I started with no experience working with APIs or graph-based data, and finished with a robust, modular tool that handles real-world data complexity, implements optimization logic, and reflects a deep understanding of the underlying transport network.

More importantly, it taught me how to approach problem-solving as a systems thinker: identifying structural weaknesses, adapting tools like `NetworkX` to my needs, and integrating multiple data sources into a coherent pipeline. It also showed me both the value and the limitations of LLM-assisted development, pushing me to refine my prompts and trust my own architectural judgment.

Not everything made it into the final build. I explored the possibility of integrating bus and cycle networks, but the scope was ultimately too large for this iteration. Bus routes require variable scheduling models and live traffic data, while cycle routing would demand a separate street-level layer and user-specific preferences. These are areas I’d like to explore in future iterations if time and resources allow.

Moving forward, I want to continue building applied AI projects that combine algorithmic thinking with real-world data integration. I’m especially interested in problems where performance, accuracy, and user experience need to be balanced within tight constraints—exactly the kind of challenge this project helped prepare me for.