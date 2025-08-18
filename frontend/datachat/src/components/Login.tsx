import React from "react";
import '../index.css'

const Login: React.FC = () => {
  return (
    // <div className="relative min-h-screen flex items-center justify-center bg-gray-900 overflow-hidden">
    //   {/* Gradient Background from Hero */}
     

    
    // </div>
    <div className="bg-gray-900 min-h-screen flex items-center">
      <div className="mx-auto max-w-7xl px-6 lg:px-8 w-full">
        <div className="relative isolate overflow-hidden bg-gray-800 px-6 pt-16 after:pointer-events-none after:absolute after:inset-0 after:inset-ring after:inset-ring-white/10 sm:rounded-3xl sm:px-16 after:sm:rounded-3xl md:pt-24 lg:flex lg:gap-x-20 lg:px-24 lg:pt-0">
          <svg
            viewBox="0 0 1024 1024"
            aria-hidden="true"
            className="absolute top-1/2 left-1/2 -z-10 size-256 -translate-y-1/2 mask-[radial-gradient(closest-side,white,transparent)] sm:left-full sm:-ml-80 lg:left-1/2 lg:ml-0 lg:-translate-x-1/2 lg:translate-y-0"
          >
            <circle r={512} cx={512} cy={512} fill="url(#grad)" fillOpacity="0.7" />
            <defs>
              <radialGradient id="grad">
                <stop stopColor="#7775D6" />
                <stop offset={1} stopColor="#E935C1" />
              </radialGradient>
            </defs>
          </svg>
            {/* Login Card */}
      <form action="" className="relative z-10">
        <div className="max-w-sm rounded-3xl bg-gradient-to-b from-sky-300 to-purple-500 p-px dark:from-gray-800 dark:to-transparent shadow-xl">
          <div className="rounded-[calc(1.5rem-1px)] bg-white px-10 p-12 dark:bg-gray-900">
            <div className="text-center">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                Sign in to your account
              </h1>
              <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
                Don’t have an account?{" "}
                <a
                  href="#"
                  className="text-blue-600 transition duration-200 hover:underline dark:text-blue-400"
                >
                  Sign up
                </a>{" "}
                for free
              </p>
            </div>

            {/* Inputs */}
            <div className="mt-8 space-y-6">
              <input
                className="w-full bg-transparent text-gray-900 dark:text-white dark:border-gray-700 rounded-md border border-gray-300 px-3 py-2 text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Your Email"
                type="email"
                name="email"
                id="email"
              />

              <input
                className="w-full bg-transparent text-gray-900 dark:text-white dark:border-gray-700 rounded-md border border-gray-300 px-3 py-2 text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Your Password"
                type="password"
                name="password"
                id="password"
              />

              <button
                type="submit"
                className="h-10 w-full bg-blue-600 hover:bg-blue-700 active:bg-blue-800 focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition duration-300 rounded-md text-white font-medium"
              >
                Sign in
              </button>
            </div>
          </div>
        </div>
      </form>

        </div>
      </div>    
    </div>
  );
};

export default Login;
