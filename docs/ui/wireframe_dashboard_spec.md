# Dashboard UI/UX Wireframe & Component Hierarchy

High-level architecture and wireframe specifications for the Real-time Parking Management Dashboard.

```mermaid
graph TD
    App[App Container] --> Header[Header & Service Status]
    App --> Metrics[Stat Cards: Occupancy, Alerts, Daily Count]
    App --> MainGrid[Main Operational Layout]
    
    MainGrid --> LeftCol[Left Column: 60%]
    MainGrid --> RightCol[Right Column: 40%]
    
    LeftCol --> SlotGrid[Parking Slot Grid with Live Badges]
    LeftCol --> TrafficChart[Hourly Inflow Traffic Chart]
    
    RightCol --> RecommendPanel[Smart Slot Recommendation Widget]
    RightCol --> AlertList[Live Security Incident Feed]
    RightCol --> SessionHistory[Active & Closed Vehicle Sessions]
```

## Component Breakdown
1. **HeaderBar**: Live WebSocket connection badge, current system time, camera selector.
2. **SummaryCards**: Quick counters for Total, Free, Occupied, Overstay, and Open Alerts.
3. **SlotGrid**: 2D floorplan visualization with category indicators.
4. **AlertFeed**: Prioritized notifications with snapshot previews.
