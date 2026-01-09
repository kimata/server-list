import { useState } from 'react';

interface ServerImageProps {
  modelName: string;
  size?: 'small' | 'large';
  className?: string;
}

/**
 * Server image component that gracefully handles missing images
 */
export function ServerImage({ modelName, size = 'small', className = '' }: ServerImageProps) {
  const [hasImage, setHasImage] = useState(true);
  const imageUrl = `/server-list/api/img/${encodeURIComponent(modelName)}.png`;

  if (!hasImage) {
    return null;
  }

  const sizeStyles = size === 'large'
    ? {
        maxWidth: '100%',
        height: 'auto',
        maxHeight: '200px',
        objectFit: 'contain' as const,
      }
    : {
        width: '150px',
        height: '150px',
        objectFit: 'contain' as const,
        flexShrink: 0,
      };

  return (
    <img
      src={imageUrl}
      alt={modelName}
      className={`server-image ${className}`}
      onError={() => setHasImage(false)}
      style={sizeStyles}
    />
  );
}
