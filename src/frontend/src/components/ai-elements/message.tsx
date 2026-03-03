'use client'

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'
import type { ComponentProps, HTMLAttributes } from 'react'

export type MessageProps = HTMLAttributes<HTMLDivElement> & {
  from: 'user' | 'assistant'
}

export const Message = ({ className, from, ...props }: MessageProps) => (
  <div
    className={cn(
      'group flex w-full items-start gap-4 py-4', // Changed from items-end to items-start for better alignment
      from === 'user' ? 'flex-row-reverse' : 'flex-row',
      className,
    )}
    {...props}
  />
)

export type MessageContentProps = HTMLAttributes<HTMLDivElement>

export const MessageContent = ({
  children,
  className,
  ...props
}: MessageContentProps) => (
  <div
    className={cn(
      'flex flex-col gap-2 rounded-lg px-4 py-3 text-sm max-w-[85%]',
      'group-[.is-user]:bg-primary group-[.is-user]:text-primary-foreground',
      // Removed secondary backgroud for assistant to match V0 clean look, just text
      className,
    )}
    {...props}
  >
    <div className="leading-relaxed">{children}</div>
  </div>
)

export type MessageAvatarProps = ComponentProps<typeof Avatar> & {
  src?: string
  name?: string
}

export const MessageAvatar = ({
  src,
  name,
  className,
  ...props
}: MessageAvatarProps) => (
  <Avatar
    className={cn('size-8 border shrink-0', className)}
    {...props}
  >
    {src && <AvatarImage alt={name} className="mt-0 mb-0" src={src} />}
    <AvatarFallback>{name?.slice(0, 2) || 'AI'}</AvatarFallback>
  </Avatar>
)
