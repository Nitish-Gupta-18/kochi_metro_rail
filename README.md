
🚆 KMRL MetroDocs AI: Dataset Portal
<div align="center"> <img src="https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=1200&q=80" alt="KMRL Header" width="100%" style="border-radius: 24px; margin-bottom: 20px;">

The Intelligence Layer for Urban Transit Data. An advanced, glassmorphism-inspired ecosystem built for Kochi Metro Rail Limited.

</div>

📖 Overview
The KMRL Dataset Portal (MetroDocs AI) is a high-performance document management system designed to streamline Kochi Metro's digital infrastructure. By combining a FastAPI backend with a cutting-edge Tailwind CSS frontend, the portal enables intelligent document exploration, role-based management, and real-time data visualization.

✨ Key Features
🎨 Premium "Railway-Flow" UI
Dynamic Motion: CSS-animated backgrounds and track dividers that mimic the movement of rail tracks.

Glassmorphism Engine: Translucent cards with high-saturation filters for a futuristic, professional aesthetic.

Adaptive Theming: Seamless dark/light mode switching with specialized "Midnight Blue" railway variants.

🤖 AI & Analytical Intelligence
Smart Visualization: Integrated Chart.js engine to track document growth and metadata distribution.

Role-Based Access (RBAC): Specialized permissions for Viewers, Contributors, and Admins.

Progressive UX: Custom "Train-Car" loading animations for asynchronous system operations.

🛡️ High-Security Auth Card
App Locking: A full-page, hardware-accelerated authentication guard that protects sensitive KMRL data.

Micro-Interactions: Magnetic buttons, tooltip indicators, and scroll-progress "trains" for an elite user experience.



flowchart TD
    %% Node Definitions
    U(fa:fa-user User / Browser)
    UI[[fa:fa-desktop Web UI]]
    API{{"fa:fa-bolt FastAPI Backend"}}
    
    subgraph Logic_Layer [Action Controller]
        direction TB
        CTRL[fa:fa-route Request Router]
    end

    subgraph Engines [Processing Engines]
        AV[fa:fa-calendar-check Availability]
        BK[fa:fa-plus-circle Booking]
        MD[fa:fa-pen-to-square Modify]
        CN[fa:fa-trash-can Cancel]
        MN[fa:fa-utensils Menu Handler]
    end

    subgraph Data_Storage [Data & Config]
        SCH[Slot Scheduler]
        CFG[(Restaurant Config)]
        CACHE[(Availability Cache)]
        STORE[(In-Memory Reservations)]
        MENU[(Menu JSON)]
    end

    %% Connections
    U --> UI
    UI --> API
    API --> CTRL

    CTRL --> AV & BK & MD & CN & MN

    AV --> SCH
    SCH --> CFG
    AV --> CACHE

    BK & MD & CN --> STORE
    MN --> MENU

    %% Dark-Mode Optimized Styling
    style U fill:#ff00ff,stroke:#fff,stroke-width:2px,color:#fff
    style API fill:#00ffcc,stroke:#00b38f,stroke-width:2px,color:#000
    style CTRL fill:#ffff00,stroke:#cca300,color:#000
    style STORE fill:#00d2ff,stroke:#0086a3,color:#000
    style CACHE fill:#00d2ff,stroke:#0086a3,color:#000
    style MENU fill:#00d2ff,stroke:#0086a3,color:#000


    Layer,Technology,Purpose
Backend,Python 3.9+ / FastAPI,High-performance API logic
Validation,Pydantic,Data integrity & schema enforcement
Server,Uvicorn,Lightning-fast ASGI server
Frontend,Tailwind CSS v3,Utility-first responsive design
Logic,Vanilla JavaScript,Reactive UI & chart integrations
Graphics,Chart.js,Interactive data analytics


