// Loading Screen Component for AI-Powered Tuxemon Frontend
// Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import React from 'react'
import { motion } from 'framer-motion'

interface LoadingScreenProps {
  message?: string
  progress?: number
}

const LoadingScreen: React.FC<LoadingScreenProps> = ({
  message = "Loading...",
  progress
}) => {
  return (
    <div className="fixed inset-0 bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900 flex items-center justify-center">
      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml,<svg width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg"><g fill="none" fill-rule="evenodd"><g fill="%23ffffff" fill-opacity="0.1"><circle cx="30" cy="30" r="2"/></g></svg>')] bg-repeat"></div>
      </div>

      {/* Main Content */}
      <div className="relative z-10 text-center max-w-md mx-auto px-6">
        {/* Logo/Title */}
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5 }}
          className="mb-8"
        >
          <h1 className="text-5xl md:text-6xl font-bold text-white mb-2">
            Tuxemon
          </h1>
          <p className="text-indigo-200 text-lg">
            AI-Powered Adventures
          </p>
        </motion.div>

        {/* Loading Animation */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.5 }}
          className="mb-6"
        >
          <div className="relative">
            {/* Spinning Pokeball */}
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
              className="w-16 h-16 mx-auto mb-4"
            >
              <div className="w-full h-full rounded-full bg-gradient-to-br from-red-500 to-red-600 border-4 border-white relative">
                <div className="absolute top-1/2 left-0 right-0 h-1 bg-black transform -translate-y-1/2"></div>
                <div className="absolute top-1/2 left-1/2 w-6 h-6 bg-white rounded-full border-2 border-gray-800 transform -translate-x-1/2 -translate-y-1/2"></div>
                <div className="absolute top-1/2 left-1/2 w-2 h-2 bg-gray-800 rounded-full transform -translate-x-1/2 -translate-y-1/2"></div>
              </div>
            </motion.div>

            {/* Loading Dots */}
            <div className="flex justify-center space-x-1">
              {[0, 1, 2].map((index) => (
                <motion.div
                  key={index}
                  animate={{
                    y: [-2, -8, -2],
                    opacity: [0.7, 1, 0.7],
                  }}
                  transition={{
                    duration: 0.8,
                    repeat: Infinity,
                    delay: index * 0.2,
                  }}
                  className="w-2 h-2 bg-white rounded-full"
                />
              ))}
            </div>
          </div>
        </motion.div>

        {/* Progress Bar */}
        {typeof progress === 'number' && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.5, duration: 0.3 }}
            className="mb-4"
          >
            <div className="w-full bg-gray-700 rounded-full h-2">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.3 }}
                className="bg-gradient-to-r from-indigo-400 to-purple-400 h-2 rounded-full"
              />
            </div>
            <p className="text-sm text-indigo-200 mt-2">
              {Math.round(progress)}%
            </p>
          </motion.div>
        )}

        {/* Loading Message */}
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.7, duration: 0.5 }}
          className="text-white text-lg mb-8"
        >
          {message}
        </motion.p>

        {/* Loading Tips */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1, duration: 0.5 }}
          className="text-indigo-300 text-sm"
        >
          <p className="mb-2">💡 Pro Tip:</p>
          <motion.p
            key={Date.now()} // Force re-animation
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
          >
            NPCs remember your interactions and develop relationships over time!
          </motion.p>
        </motion.div>

        {/* Version Info */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2, duration: 0.5 }}
          className="absolute bottom-6 left-1/2 transform -translate-x-1/2 text-xs text-indigo-400"
        >
          <p>v1.0.0 | Mobile-First Edition</p>
        </motion.div>
      </div>

      {/* Floating Particles */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {Array.from({ length: 20 }).map((_, i) => (
          <motion.div
            key={i}
            initial={{
              x: Math.random() * window.innerWidth,
              y: window.innerHeight + 50,
              opacity: 0,
            }}
            animate={{
              y: -50,
              opacity: [0, 0.5, 0],
            }}
            transition={{
              duration: Math.random() * 10 + 5,
              repeat: Infinity,
              delay: Math.random() * 5,
            }}
            className="absolute w-2 h-2 bg-white rounded-full"
          />
        ))}
      </div>
    </div>
  )
}

export default LoadingScreen