import React from 'react'
import { motion } from 'framer-motion'
import { Check } from 'lucide-react'
import { cn } from '../lib/utils'

interface Platform {
  id: string
  name: string
  icon: string
  color: string
  gradient: string
  description: string
}

const platforms: Platform[] = [
  {
    id: 'tiktok',
    name: 'TikTok',
    icon: '🎵',
    color: 'text-pink-600',
    gradient: 'tiktok-gradient',
    description: 'Short-form videos'
  },
  {
    id: 'facebook',
    name: 'Facebook',
    icon: '📘',
    color: 'text-blue-600',
    gradient: 'facebook-gradient',
    description: 'Posts & Stories'
  },
  {
    id: 'youtube',
    name: 'YouTube',
    icon: '📺',
    color: 'text-red-600',
    gradient: 'youtube-gradient',
    description: 'Videos & Shorts'
  },
  {
    id: 'instagram',
    name: 'Instagram',
    icon: '📸',
    color: 'text-purple-600',
    gradient: 'instagram-gradient',
    description: 'Photos & Reels'
  },
  {
    id: 'twitter',
    name: 'Twitter',
    icon: '🐦',
    color: 'text-blue-500',
    gradient: 'twitter-gradient',
    description: 'Tweets & Threads'
  },
  {
    id: 'linkedin',
    name: 'LinkedIn',
    icon: '💼',
    color: 'text-blue-700',
    gradient: 'bg-gradient-to-br from-blue-700 to-blue-800',
    description: 'Professional posts'
  }
]

interface PlatformSelectorProps {
  selectedPlatforms: string[]
  onPlatformChange: (platforms: string[]) => void
}

export function PlatformSelector({ selectedPlatforms, onPlatformChange }: PlatformSelectorProps) {
  const togglePlatform = (platformId: string) => {
    if (selectedPlatforms.includes(platformId)) {
      onPlatformChange(selectedPlatforms.filter(id => id !== platformId))
    } else {
      onPlatformChange([...selectedPlatforms, platformId])
    }
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-slate-800 mb-2">Select Platforms</h2>
        <p className="text-slate-600">Choose which social media platforms you want to manage</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {platforms.map((platform, index) => {
          const isSelected = selectedPlatforms.includes(platform.id)
          
          return (
            <motion.div
              key={platform.id}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <button
                onClick={() => togglePlatform(platform.id)}
                className={cn(
                  "relative w-full p-4 rounded-2xl border-2 transition-all duration-300",
                  "hover:shadow-lg hover:shadow-slate-200",
                  isSelected
                    ? "border-blue-500 bg-blue-50 shadow-lg shadow-blue-100"
                    : "border-slate-200 bg-white hover:border-slate-300"
                )}
              >
                {/* Selection indicator */}
                {isSelected && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    className="absolute -top-2 -right-2 w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center"
                  >
                    <Check className="w-4 h-4 text-white" />
                  </motion.div>
                )}

                {/* Platform icon */}
                <div className="text-3xl mb-2">{platform.icon}</div>
                
                {/* Platform name */}
                <h3 className={cn("font-semibold text-sm mb-1", platform.color)}>
                  {platform.name}
                </h3>
                
                {/* Platform description */}
                <p className="text-xs text-slate-500">{platform.description}</p>

                {/* Gradient accent */}
                <div className={cn(
                  "absolute bottom-0 left-0 right-0 h-1 rounded-b-2xl transition-opacity",
                  platform.gradient,
                  isSelected ? "opacity-100" : "opacity-0"
                )} />
              </button>
            </motion.div>
          )
        })}
      </div>

      {selectedPlatforms.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center p-4 bg-blue-50 rounded-xl border border-blue-200"
        >
          <p className="text-blue-800 font-medium">
            {selectedPlatforms.length} platform{selectedPlatforms.length > 1 ? 's' : ''} selected
          </p>
          <p className="text-blue-600 text-sm mt-1">
            Ready to create content for: {selectedPlatforms.map(id => 
              platforms.find(p => p.id === id)?.name
            ).join(', ')}
          </p>
        </motion.div>
      )}
    </div>
  )
}