graph TB
    subgraph Frontend[Frontend React TypeScript]
        HomePage[HomePage]
        LoginPage[LoginPage] 
        ProductsPage[ProductsPage]
        CartPage[CartPage]
        AuthStore[AuthStore]
        API[API Client]
    end
    
    subgraph Backend[QuickMart Backend FastAPI]
        AuthAPI[Auth API]
        ProductsAPI[Products API]
        CouponsAPI[Coupons API]
        AdminAPI[Admin API]
        DatabaseManager[Database Manager]
    end
    
    subgraph RecoEngine[RecoEngine]
        PredictAPI[Predict API]
        IngestAPI[Ingest API]
        ModelPredictor[Model Predictor]
        NudgeEngine[Nudge Engine]
    end
    
    subgraph DataStorage[Data Storage]
        UsersSet[Users Set]
        ProductsSet[Products Set]
        CouponsSet[Coupons Set]
        FeaturesSet[Features Set]
    end

    LoginPage --> AuthAPI
    ProductsPage --> ProductsAPI
    CartPage --> CouponsAPI
    
    AuthAPI --> DatabaseManager
    ProductsAPI --> DatabaseManager
    CouponsAPI --> DatabaseManager
    AdminAPI --> DatabaseManager
    
    AuthAPI --> PredictAPI
    AuthAPI --> IngestAPI
    PredictAPI --> ModelPredictor
    PredictAPI --> NudgeEngine
    NudgeEngine --> CouponsAPI
    
    DatabaseManager --> UsersSet
    DatabaseManager --> ProductsSet
    DatabaseManager --> CouponsSet
    DatabaseManager --> FeaturesSet

    classDef frontend fill:#e1f5fe
    classDef backend fill:#f3e5f5
    classDef reco fill:#fff3e0
    classDef data fill:#e8f5e8
    
    class HomePage,LoginPage,ProductsPage,CartPage,AuthStore,API frontend
    class AuthAPI,ProductsAPI,CouponsAPI,AdminAPI,DatabaseManager backend
    class PredictAPI,IngestAPI,ModelPredictor,NudgeEngine reco
    class UsersSet,ProductsSet,CouponsSet,FeaturesSet data