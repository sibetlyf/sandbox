'use client'

import { cn } from '@/lib/utils'
import ReactMarkdown from 'react-markdown'
import { type ComponentProps, memo } from 'react'

type ResponseProps = ComponentProps<'div'> & { children: string }

export const Response = memo(
  ({ className, children, ...props }: ResponseProps) => (
    <div
      className={cn(
        'size-full [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 prose dark:prose-invert max-w-none text-sm leading-relaxed',
        className,
      )}
      {...props}
    >
        <ReactMarkdown>{children}</ReactMarkdown>
    </div>
  ),
  (prevProps, nextProps) => prevProps.children === nextProps.children,
)

Response.displayName = 'Response'
