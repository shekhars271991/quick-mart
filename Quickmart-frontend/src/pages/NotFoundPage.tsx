import { ArrowLeft, Home } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function NotFoundPage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
            <div className="max-w-md w-full text-center">
                <div className="mb-8">
                    <h1 className="text-9xl font-bold text-primary-600">404</h1>
                    <h2 className="text-2xl font-semibold text-gray-900 mt-4">Page Not Found</h2>
                    <p className="text-gray-600 mt-2">
                        Sorry, we couldn't find the page you're looking for.
                    </p>
                </div>

                <div className="space-y-4">
                    <Link
                        to="/"
                        className="btn-primary btn-lg inline-flex items-center"
                    >
                        <Home className="w-5 h-5 mr-2" />
                        Go Home
                    </Link>

                    <button
                        onClick={() => window.history.back()}
                        className="btn-outline btn-lg inline-flex items-center ml-4"
                    >
                        <ArrowLeft className="w-5 h-5 mr-2" />
                        Go Back
                    </button>
                </div>
            </div>
        </div>
    )
}
