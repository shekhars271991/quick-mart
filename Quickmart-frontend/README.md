# QuickMart Frontend

A modern, responsive React application for the QuickMart e-commerce platform with AI-powered recommendations and smart coupon management.

## 🚀 Features

- **Modern React Architecture**: Built with React 18, TypeScript, and Vite
- **Responsive Design**: Mobile-first design with Tailwind CSS
- **Authentication**: JWT-based authentication with protected routes
- **State Management**: Zustand for global state management
- **API Integration**: Axios with React Query for efficient data fetching
- **Shopping Cart**: Persistent cart with local storage
- **Product Catalog**: Advanced search, filtering, and product browsing
- **Coupon System**: AI-powered coupon recommendations and management
- **Professional UI**: Clean, modern interface following industry best practices

## 🛠️ Tech Stack

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: Zustand
- **Data Fetching**: React Query + Axios
- **Routing**: React Router v6
- **Forms**: React Hook Form
- **Icons**: Lucide React
- **Notifications**: React Hot Toast

## 📦 Installation

1. **Navigate to the frontend directory**:
   ```bash
   cd Quickmart-frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Create environment file**:
   ```bash
   cp .env.example .env
   ```

4. **Update environment variables** (if needed):
   ```env
   VITE_API_URL=http://localhost:3010
   ```

## 🚀 Development

1. **Start the development server**:
   ```bash
   npm run dev
   ```

2. **Open your browser**:
   Navigate to `http://localhost:3000`

3. **Start coding**:
   The app will hot-reload as you make changes

## 🏗️ Build

1. **Build for production**:
   ```bash
   npm run build
   ```

2. **Preview the build**:
   ```bash
   npm run preview
   ```

## 🧪 Development Commands

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linting
npm run lint

# Fix linting issues
npm run lint:fix

# Type checking
npm run type-check
```

## 📁 Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── auth/           # Authentication components
│   └── layout/         # Layout components (Header, Footer)
├── lib/                # Utilities and configurations
│   └── api.ts          # API client and methods
├── pages/              # Page components
│   ├── auth/           # Login, Register pages
│   ├── products/       # Product listing, detail pages
│   ├── cart/           # Shopping cart page
│   └── ...
├── stores/             # Zustand state stores
│   ├── authStore.ts    # Authentication state
│   └── cartStore.ts    # Shopping cart state
├── types/              # TypeScript type definitions
└── main.tsx           # Application entry point
```

## 🔗 API Integration

The frontend integrates with the QuickMart backend API running on `http://localhost:3010`. Key API endpoints:

- **Authentication**: `/api/auth/*`
- **Products**: `/api/products/*`
- **Coupons**: `/api/coupons/*`
- **Users**: `/api/users/*`

## 🎨 Design System

The app uses a custom design system built with Tailwind CSS:

- **Colors**: Primary (blue), secondary (gray), success (green), warning (yellow), error (red)
- **Typography**: Inter font family with responsive text scales
- **Components**: Consistent button styles, form inputs, cards, and badges
- **Animations**: Subtle fade-in and slide-up animations

## 🔐 Authentication Flow

1. **Registration**: Users can create accounts with email/password
2. **Login**: JWT token-based authentication
3. **Protected Routes**: Automatic redirection for unauthenticated users
4. **Token Management**: Automatic token refresh and logout on expiry

## 🛒 Shopping Experience

- **Product Discovery**: Browse, search, and filter products
- **Smart Recommendations**: AI-powered product suggestions
- **Shopping Cart**: Persistent cart with quantity management
- **Coupon System**: Automatic coupon application and management
- **Responsive Design**: Optimized for mobile and desktop

## 🚀 Deployment

1. **Build the application**:
   ```bash
   npm run build
   ```

2. **Deploy the `dist` folder** to your preferred hosting service:
   - Vercel
   - Netlify
   - AWS S3 + CloudFront
   - Any static hosting service

## 🔧 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:3010` |
| `VITE_APP_NAME` | Application name | `QuickMart` |
| `VITE_APP_VERSION` | Application version | `1.0.0` |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## 📄 License

This project is part of the QuickMart e-commerce platform.

---

**Happy Shopping! 🛍️**
