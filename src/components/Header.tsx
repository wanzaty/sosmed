import React from 'react'
import { motion } from 'framer-motion'
import { Share2, Settings, Bell, User } from 'lucide-react'
import { Button } from './ui/button'

export function Header() {
  return (
    <motion.header 
      className="bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0 z-50"
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <motion.div 
            className="flex items-center gap-3"
            whileHover={{ scale: 1.05 }}
            transition={{ type: "spring", stiffness: 400, damping: 10 }}
          >
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
              <Share2 className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-800">SocialHub</h1>
              <p className="text-xs text-slate-500">Multi-Platform Manager</p>
            </div>
          </motion.div>

          {/* Navigation */}
          <nav className="hidden md:flex items-center gap-6">
            <Button variant="ghost" size="sm" className="text-slate-600 hover:text-slate-800">
              Dashboard
            </Button>
            <Button variant="ghost" size="sm" className="text-slate-600 hover:text-slate-800">
              Content
            </Button>
            <Button variant="ghost" size="sm" className="text-slate-600 hover:text-slate-800">
              Analytics
            </Button>
          </nav>

          {/* Actions */}
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" className="relative">
              <Bell className="w-4 h-4" />
              <span className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full"></span>
            </Button>
            <Button variant="ghost" size="sm">
              <Settings className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="sm">
              <User className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </motion.header>
  )
}