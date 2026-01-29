// Notification System Component for AI-Powered Tuxemon Frontend
// Austin Kidwell | Intellegix | Mobile-First Pokemon-Style Game

import React, { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useUI } from '../hooks/useGameStore'

interface NotificationAction {
  label: string
  action: () => void
  style?: 'primary' | 'secondary' | 'danger'
}

interface Notification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message: string
  duration?: number
  actions?: NotificationAction[]
  persistent?: boolean
}

const NotificationSystem: React.FC = () => {
  const { notifications, removeNotification } = useUI()

  // Auto-remove notifications after duration
  useEffect(() => {
    const timers: { [key: string]: NodeJS.Timeout } = {}

    notifications.forEach((notification) => {
      if (!notification.persistent && notification.duration && notification.duration > 0) {
        timers[notification.id] = setTimeout(() => {
          removeNotification(notification.id)
        }, notification.duration)
      }
    })

    return () => {
      Object.values(timers).forEach(clearTimeout)
    }
  }, [notifications, removeNotification])

  const getNotificationIcon = (type: Notification['type']): string => {
    switch (type) {
      case 'success':
        return '✅'
      case 'warning':
        return '⚠️'
      case 'error':
        return '❌'
      default:
        return 'ℹ️'
    }
  }

  const getNotificationColors = (type: Notification['type']) => {
    switch (type) {
      case 'success':
        return {
          bg: 'bg-green-500/90',
          border: 'border-green-400/50',
          text: 'text-green-50',
        }
      case 'warning':
        return {
          bg: 'bg-yellow-500/90',
          border: 'border-yellow-400/50',
          text: 'text-yellow-50',
        }
      case 'error':
        return {
          bg: 'bg-red-500/90',
          border: 'border-red-400/50',
          text: 'text-red-50',
        }
      default:
        return {
          bg: 'bg-blue-500/90',
          border: 'border-blue-400/50',
          text: 'text-blue-50',
        }
    }
  }

  const getActionButtonColors = (style: NotificationAction['style'] = 'secondary') => {
    switch (style) {
      case 'primary':
        return 'bg-white text-gray-900 hover:bg-gray-100'
      case 'danger':
        return 'bg-red-600 text-white hover:bg-red-700'
      default:
        return 'bg-white/20 text-white hover:bg-white/30'
    }
  }

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-sm w-full">
      <AnimatePresence mode="popLayout">
        {notifications.map((notification) => {
          const colors = getNotificationColors(notification.type)
          const icon = getNotificationIcon(notification.type)

          return (
            <motion.div
              key={notification.id}
              layout
              initial={{
                opacity: 0,
                y: -50,
                scale: 0.95,
              }}
              animate={{
                opacity: 1,
                y: 0,
                scale: 1,
              }}
              exit={{
                opacity: 0,
                scale: 0.95,
                y: -20,
                transition: { duration: 0.2 },
              }}
              transition={{
                type: 'spring',
                damping: 25,
                stiffness: 300,
              }}
              className={`
                ${colors.bg} backdrop-blur-md rounded-lg border ${colors.border}
                shadow-2xl p-4 ${colors.text} max-w-sm
              `}
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center space-x-2 flex-1">
                  <span className="text-lg flex-shrink-0">{icon}</span>
                  <h4 className="font-semibold text-sm truncate">
                    {notification.title}
                  </h4>
                </div>

                {/* Close Button */}
                {!notification.persistent && (
                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={() => removeNotification(notification.id)}
                    className="text-white/70 hover:text-white flex-shrink-0 ml-2 w-6 h-6 flex items-center justify-center rounded-full hover:bg-white/10"
                  >
                    ✕
                  </motion.button>
                )}
              </div>

              {/* Message */}
              <p className="text-sm leading-relaxed mb-3">
                {notification.message}
              </p>

              {/* Actions */}
              {notification.actions && notification.actions.length > 0 && (
                <div className="flex space-x-2 mt-3">
                  {notification.actions.map((action, index) => (
                    <motion.button
                      key={index}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => {
                        action.action()
                        if (!notification.persistent) {
                          removeNotification(notification.id)
                        }
                      }}
                      className={`
                        px-3 py-1.5 rounded-md text-xs font-medium transition-colors
                        ${getActionButtonColors(action.style)}
                      `}
                    >
                      {action.label}
                    </motion.button>
                  ))}
                </div>
              )}

              {/* Progress Bar for Timed Notifications */}
              {!notification.persistent && notification.duration && notification.duration > 0 && (
                <motion.div
                  initial={{ width: '100%' }}
                  animate={{ width: '0%' }}
                  transition={{ duration: notification.duration / 1000, ease: 'linear' }}
                  className="absolute bottom-0 left-0 h-1 bg-white/30 rounded-b-lg"
                />
              )}
            </motion.div>
          )
        })}
      </AnimatePresence>

      {/* Toast Area Placeholder for Mobile Positioning */}
      {notifications.length === 0 && (
        <div className="hidden">
          {/* This ensures the toast area is properly positioned on mobile */}
        </div>
      )}
    </div>
  )
}

// Helper function to add notifications (for use in components)
export const useNotifications = () => {
  const { addNotification, removeNotification, notifications } = useUI()

  const showNotification = (
    type: Notification['type'],
    title: string,
    message: string,
    options?: {
      duration?: number
      actions?: NotificationAction[]
      persistent?: boolean
    }
  ) => {
    const notification: Notification = {
      id: `notification-${Date.now()}-${Math.random()}`,
      type,
      title,
      message,
      duration: options?.duration || 5000,
      actions: options?.actions,
      persistent: options?.persistent || false,
    }

    addNotification(notification)
    return notification.id
  }

  const showSuccess = (title: string, message: string, options?: any) =>
    showNotification('success', title, message, options)

  const showError = (title: string, message: string, options?: any) =>
    showNotification('error', title, message, options)

  const showWarning = (title: string, message: string, options?: any) =>
    showNotification('warning', title, message, options)

  const showInfo = (title: string, message: string, options?: any) =>
    showNotification('info', title, message, options)

  return {
    showNotification,
    showSuccess,
    showError,
    showWarning,
    showInfo,
    removeNotification,
    notifications,
  }
}

export default NotificationSystem