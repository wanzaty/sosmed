import React, { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import { useDropzone } from 'react-dropzone'
import { Upload, Video, Image, FileText, Send, Calendar, Clock, Sparkles } from 'lucide-react'
import { Button } from './ui/button'
import { Textarea } from './ui/textarea'
import { Input } from './ui/input'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Badge } from './ui/badge'
import { Progress } from './ui/progress'
import { useToast } from './ui/use-toast'

interface ContentCreatorProps {
  selectedPlatforms: string[]
}

interface MediaFile {
  file: File
  preview: string
  type: 'image' | 'video'
}

export function ContentCreator({ selectedPlatforms }: ContentCreatorProps) {
  const [mediaFiles, setMediaFiles] = useState<MediaFile[]>([])
  const [content, setContent] = useState('')
  const [title, setTitle] = useState('')
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const { toast } = useToast()

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map(file => ({
      file,
      preview: URL.createObjectURL(file),
      type: file.type.startsWith('video/') ? 'video' as const : 'image' as const
    }))
    
    setMediaFiles(prev => [...prev, ...newFiles])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.gif'],
      'video/*': ['.mp4', '.mov', '.avi', '.mkv']
    },
    maxSize: 100 * 1024 * 1024 // 100MB
  })

  const removeFile = (index: number) => {
    setMediaFiles(prev => {
      const newFiles = [...prev]
      URL.revokeObjectURL(newFiles[index].preview)
      newFiles.splice(index, 1)
      return newFiles
    })
  }

  const handlePublish = async () => {
    if (selectedPlatforms.length === 0) {
      toast({
        title: "No platforms selected",
        description: "Please select at least one platform to publish to.",
        variant: "destructive"
      })
      return
    }

    if (!content.trim() && mediaFiles.length === 0) {
      toast({
        title: "No content to publish",
        description: "Please add some text or media files.",
        variant: "destructive"
      })
      return
    }

    setIsUploading(true)
    setUploadProgress(0)

    // Simulate upload progress
    const interval = setInterval(() => {
      setUploadProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval)
          setIsUploading(false)
          toast({
            title: "Content published successfully!",
            description: `Your content has been published to ${selectedPlatforms.length} platform${selectedPlatforms.length > 1 ? 's' : ''}.`
          })
          // Reset form
          setContent('')
          setTitle('')
          setMediaFiles([])
          return 100
        }
        return prev + Math.random() * 15
      })
    }, 200)
  }

  const handleSchedule = () => {
    toast({
      title: "Schedule feature",
      description: "Scheduling feature will be available soon!"
    })
  }

  const generateAIContent = () => {
    const suggestions = [
      "🚀 Exciting news! Just launched something amazing...",
      "💡 Here's a quick tip that changed everything for me:",
      "🌟 Behind the scenes of today's creative process...",
      "🔥 This trend is taking over - here's my take:",
      "✨ Grateful for this incredible journey and all of you!"
    ]
    
    const randomSuggestion = suggestions[Math.floor(Math.random() * suggestions.length)]
    setContent(randomSuggestion)
    
    toast({
      title: "AI content generated!",
      description: "Feel free to customize the suggested content."
    })
  }

  if (selectedPlatforms.length === 0) {
    return (
      <Card className="text-center py-12">
        <CardContent>
          <div className="text-6xl mb-4">🎯</div>
          <h3 className="text-xl font-semibold mb-2">Select Platforms First</h3>
          <p className="text-slate-600">
            Choose which social media platforms you want to create content for.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Selected Platforms */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Send className="w-5 h-5" />
            Publishing to {selectedPlatforms.length} platform{selectedPlatforms.length > 1 ? 's' : ''}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {selectedPlatforms.map(platform => (
              <Badge key={platform} variant="secondary" className="capitalize">
                {platform}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Content Input */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  Content
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={generateAIContent}
                  className="flex items-center gap-2"
                >
                  <Sparkles className="w-4 h-4" />
                  AI Suggest
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input
                placeholder="Title (optional)"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
              <Textarea
                placeholder="What's on your mind? Share your story, thoughts, or updates..."
                value={content}
                onChange={(e) => setContent(e.target.value)}
                rows={6}
                className="resize-none"
              />
              <div className="text-sm text-slate-500">
                {content.length}/2200 characters
              </div>
            </CardContent>
          </Card>

          {/* Media Upload */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="w-5 h-5" />
                Media Files
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                  isDragActive
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-slate-300 hover:border-slate-400'
                }`}
              >
                <input {...getInputProps()} />
                <Upload className="w-12 h-12 mx-auto mb-4 text-slate-400" />
                {isDragActive ? (
                  <p className="text-blue-600">Drop the files here...</p>
                ) : (
                  <div>
                    <p className="text-slate-600 mb-2">
                      Drag & drop files here, or click to select
                    </p>
                    <p className="text-sm text-slate-500">
                      Supports images and videos up to 100MB
                    </p>
                  </div>
                )}
              </div>

              {/* File Preview */}
              {mediaFiles.length > 0 && (
                <div className="mt-4 grid grid-cols-2 gap-4">
                  {mediaFiles.map((file, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="relative group"
                    >
                      <div className="aspect-square rounded-lg overflow-hidden bg-slate-100">
                        {file.type === 'video' ? (
                          <video
                            src={file.preview}
                            className="w-full h-full object-cover"
                            controls
                          />
                        ) : (
                          <img
                            src={file.preview}
                            alt="Preview"
                            className="w-full h-full object-cover"
                          />
                        )}
                      </div>
                      <button
                        onClick={() => removeFile(index)}
                        className="absolute top-2 right-2 w-6 h-6 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-sm"
                      >
                        ×
                      </button>
                      <div className="absolute bottom-2 left-2">
                        {file.type === 'video' ? (
                          <Video className="w-4 h-4 text-white" />
                        ) : (
                          <Image className="w-4 h-4 text-white" />
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Preview & Actions */}
        <div className="space-y-4">
          {/* Preview */}
          <Card>
            <CardHeader>
              <CardTitle>Preview</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-slate-50 rounded-lg p-4 min-h-[200px]">
                {title && (
                  <h3 className="font-semibold text-lg mb-2">{title}</h3>
                )}
                {content ? (
                  <p className="text-slate-700 whitespace-pre-wrap">{content}</p>
                ) : (
                  <p className="text-slate-400 italic">Your content will appear here...</p>
                )}
                {mediaFiles.length > 0 && (
                  <div className="mt-4 text-sm text-slate-500">
                    📎 {mediaFiles.length} file{mediaFiles.length > 1 ? 's' : ''} attached
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Publishing Options */}
          <Card>
            <CardHeader>
              <CardTitle>Publishing Options</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {isUploading && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span>Publishing...</span>
                    <span>{Math.round(uploadProgress)}%</span>
                  </div>
                  <Progress value={uploadProgress} />
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <Button
                  onClick={handlePublish}
                  disabled={isUploading}
                  className="flex items-center gap-2"
                >
                  <Send className="w-4 h-4" />
                  {isUploading ? 'Publishing...' : 'Publish Now'}
                </Button>
                <Button
                  variant="outline"
                  onClick={handleSchedule}
                  disabled={isUploading}
                  className="flex items-center gap-2"
                >
                  <Calendar className="w-4 h-4" />
                  Schedule
                </Button>
              </div>

              <div className="text-xs text-slate-500 space-y-1">
                <p>• Content will be optimized for each platform</p>
                <p>• Hashtags will be automatically suggested</p>
                <p>• Media will be resized appropriately</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}