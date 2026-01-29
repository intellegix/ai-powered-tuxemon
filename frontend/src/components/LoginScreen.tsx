// Login Screen Component for AI-Powered Tuxemon Frontend
// Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth, useUI } from '../hooks/useGameStore'
import { apiService } from '../services/api'

interface LoginScreenProps {
  isRegister?: boolean
}

const LoginScreen: React.FC<LoginScreenProps> = ({ isRegister = false }) => {
  const { login, register } = useAuth()
  const { setError, setLoading, ui } = useUI()

  const [mode, setMode] = useState<'login' | 'register'>(isRegister ? 'register' : 'login')
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  })
  const [validationErrors, setValidationErrors] = useState<string[]>([])

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    setValidationErrors([])
    setError(null)
  }

  const validateForm = (): boolean => {
    const errors: string[] = []

    if (formData.username.length < 3) {
      errors.push('Username must be at least 3 characters')
    }

    if (mode === 'register') {
      if (!formData.email.includes('@')) {
        errors.push('Valid email address required')
      }
      if (formData.password !== formData.confirmPassword) {
        errors.push('Passwords do not match')
      }
    }

    if (formData.password.length < 6) {
      errors.push('Password must be at least 6 characters')
    }

    setValidationErrors(errors)
    return errors.length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateForm()) {
      return
    }

    try {
      setLoading(true)
      setError(null)

      if (mode === 'register') {
        const result = await register({
          username: formData.username,
          email: formData.email,
          password: formData.password,
        })

        if (result.success) {
          // Automatically log in after successful registration
          await login({
            username: formData.username,
            password: formData.password,
          })
        } else {
          setError(result.error || 'Registration failed')
        }
      } else {
        const result = await login({
          username: formData.username,
          password: formData.password,
        })

        if (!result.success) {
          setError(result.error || 'Login failed')
        }
      }
    } catch (error: any) {
      console.error('Auth error:', error)
      setError(error.message || 'Authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-900 via-purple-900 to-indigo-900 flex items-center justify-center px-4">
      {/* Background Elements */}
      <div className="absolute inset-0 overflow-hidden">
        <motion.div
          animate={{
            rotate: 360,
          }}
          transition={{
            duration: 50,
            repeat: Infinity,
            ease: 'linear',
          }}
          className="absolute -top-40 -left-40 w-80 h-80 bg-gradient-to-r from-purple-400 to-pink-400 rounded-full opacity-20 blur-3xl"
        />
        <motion.div
          animate={{
            rotate: -360,
          }}
          transition={{
            duration: 40,
            repeat: Infinity,
            ease: 'linear',
          }}
          className="absolute -bottom-32 -right-32 w-96 h-96 bg-gradient-to-r from-blue-400 to-indigo-400 rounded-full opacity-20 blur-3xl"
        />
      </div>

      {/* Main Content */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10 w-full max-w-md"
      >
        {/* Header */}
        <div className="text-center mb-8">
          <motion.h1
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.2, duration: 0.3 }}
            className="text-4xl md:text-5xl font-bold text-white mb-2"
          >
            Tuxemon
          </motion.h1>
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4, duration: 0.3 }}
            className="text-blue-200 text-lg"
          >
            Begin your AI-powered adventure
          </motion.p>
        </div>

        {/* Auth Form */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.3, duration: 0.4 }}
          className="bg-white/10 backdrop-blur-lg rounded-2xl p-8 shadow-2xl border border-white/20"
        >
          {/* Mode Toggle */}
          <div className="flex mb-6 bg-black/20 rounded-lg p-1">
            {['login', 'register'].map((modeOption) => (
              <button
                key={modeOption}
                onClick={() => setMode(modeOption as 'login' | 'register')}
                className={`flex-1 py-2 px-4 rounded-md font-medium transition-all duration-200 ${
                  mode === modeOption
                    ? 'bg-white text-gray-900 shadow-md'
                    : 'text-white/70 hover:text-white hover:bg-white/5'
                }`}
              >
                {modeOption === 'login' ? 'Login' : 'Register'}
              </button>
            ))}
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username */}
            <motion.div
              layout
              className="space-y-2"
            >
              <label className="block text-white text-sm font-medium">
                Username
              </label>
              <input
                type="text"
                value={formData.username}
                onChange={(e) => handleInputChange('username', e.target.value)}
                className="w-full px-4 py-3 bg-black/20 border border-white/30 rounded-lg text-white placeholder-white/50 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-400/20 transition-colors"
                placeholder="Enter your username"
                disabled={ui.loading}
                required
              />
            </motion.div>

            {/* Email (Register only) */}
            <AnimatePresence mode="wait">
              {mode === 'register' && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="space-y-2"
                >
                  <label className="block text-white text-sm font-medium">
                    Email
                  </label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => handleInputChange('email', e.target.value)}
                    className="w-full px-4 py-3 bg-black/20 border border-white/30 rounded-lg text-white placeholder-white/50 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-400/20 transition-colors"
                    placeholder="Enter your email"
                    disabled={ui.loading}
                    required
                  />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Password */}
            <motion.div
              layout
              className="space-y-2"
            >
              <label className="block text-white text-sm font-medium">
                Password
              </label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) => handleInputChange('password', e.target.value)}
                className="w-full px-4 py-3 bg-black/20 border border-white/30 rounded-lg text-white placeholder-white/50 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-400/20 transition-colors"
                placeholder="Enter your password"
                disabled={ui.loading}
                required
              />
            </motion.div>

            {/* Confirm Password (Register only) */}
            <AnimatePresence mode="wait">
              {mode === 'register' && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="space-y-2"
                >
                  <label className="block text-white text-sm font-medium">
                    Confirm Password
                  </label>
                  <input
                    type="password"
                    value={formData.confirmPassword}
                    onChange={(e) => handleInputChange('confirmPassword', e.target.value)}
                    className="w-full px-4 py-3 bg-black/20 border border-white/30 rounded-lg text-white placeholder-white/50 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-400/20 transition-colors"
                    placeholder="Confirm your password"
                    disabled={ui.loading}
                    required
                  />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Validation Errors */}
            <AnimatePresence>
              {validationErrors.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="bg-red-500/20 border border-red-500/50 rounded-lg p-3"
                >
                  {validationErrors.map((error, index) => (
                    <p key={index} className="text-red-200 text-sm">
                      • {error}
                    </p>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Submit Button */}
            <motion.button
              type="submit"
              disabled={ui.loading}
              whileHover={{ scale: ui.loading ? 1 : 1.02 }}
              whileTap={{ scale: ui.loading ? 1 : 0.98 }}
              className={`w-full py-3 px-4 rounded-lg font-medium text-white transition-all duration-200 ${
                ui.loading
                  ? 'bg-gray-600 cursor-not-allowed'
                  : 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 shadow-lg hover:shadow-xl'
              }`}
            >
              {ui.loading ? (
                <div className="flex items-center justify-center space-x-2">
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    className="w-4 h-4 border-2 border-white border-t-transparent rounded-full"
                  />
                  <span>Processing...</span>
                </div>
              ) : (
                mode === 'register' ? 'Create Account' : 'Sign In'
              )}
            </motion.button>
          </form>

          {/* Footer */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6, duration: 0.3 }}
            className="mt-6 text-center text-white/60 text-sm"
          >
            {mode === 'register' ? (
              <p>
                By creating an account, you agree to our{' '}
                <a href="#" className="text-blue-300 hover:text-blue-200 underline">
                  Terms of Service
                </a>
              </p>
            ) : (
              <p>
                Demo credentials: username: <code className="bg-black/30 px-1 rounded">demo</code>, password: <code className="bg-black/30 px-1 rounded">demo123</code>
              </p>
            )}
          </motion.div>
        </motion.div>

        {/* Features Preview */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8, duration: 0.4 }}
          className="mt-8 grid grid-cols-2 gap-4 text-center"
        >
          <div className="bg-white/5 backdrop-blur-sm rounded-lg p-4 border border-white/10">
            <div className="text-2xl mb-2">🤖</div>
            <p className="text-white/80 text-sm">AI NPCs with Memory</p>
          </div>
          <div className="bg-white/5 backdrop-blur-sm rounded-lg p-4 border border-white/10">
            <div className="text-2xl mb-2">📱</div>
            <p className="text-white/80 text-sm">Mobile-First Design</p>
          </div>
        </motion.div>
      </motion.div>
    </div>
  )
}

export default LoginScreen