import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Colors, Spacing, Radius, Typography } from '../utils/theme';
import { Message } from '../types';
import { ToolCallBadge } from './ToolCallBadge';
import { SourcesPanel } from './SourcesPanel';
import { StreamingDots } from './StreamingDots';

interface Props {
  message: Message;
}

export const ChatBubble: React.FC<Props> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <View style={[styles.wrapper, isUser ? styles.wrapperUser : styles.wrapperAssistant]}>
      {!isUser && (
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>AI</Text>
        </View>
      )}

      <View style={[styles.bubble, isUser ? styles.bubbleUser : styles.bubbleAssistant]}>
        {/* Tool calls above the text */}
        {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
          <View style={styles.toolCalls}>
            {message.toolCalls.map((tc, i) => (
              <ToolCallBadge key={i} toolCall={tc} />
            ))}
          </View>
        )}

        {/* Main content */}
        {message.isStreaming && !message.content ? (
          <StreamingDots />
        ) : (
          <Text style={isUser ? styles.textUser : styles.textAssistant}>
            {message.content}
          </Text>
        )}

        {/* Sources */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <SourcesPanel sources={message.sources} />
        )}

        {/* Timestamp */}
        <Text style={styles.timestamp}>
          {formatTime(message.timestamp)}
        </Text>
      </View>
    </View>
  );
};

function formatTime(date: Date): string {
  try {
    return date.toLocaleTimeString('tr-TR', {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

const styles = StyleSheet.create({
  wrapper: {
    flexDirection: 'row',
    marginVertical: Spacing.xs,
    paddingHorizontal: Spacing.md,
    alignItems: 'flex-end',
    gap: Spacing.sm,
  },
  wrapperUser: {
    justifyContent: 'flex-end',
  },
  wrapperAssistant: {
    justifyContent: 'flex-start',
  },
  avatar: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 2,
  },
  avatarText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#fff',
  },
  bubble: {
    maxWidth: '82%',
    borderRadius: Radius.lg,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
  },
  bubbleUser: {
    backgroundColor: Colors.primary,
    borderBottomRightRadius: Radius.sm,
  },
  bubbleAssistant: {
    backgroundColor: Colors.bgCard,
    borderBottomLeftRadius: Radius.sm,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  textUser: {
    ...Typography.body,
    color: '#fff',
    lineHeight: 20,
  },
  textAssistant: {
    ...Typography.body,
    color: Colors.textPrimary,
    lineHeight: 22,
  },
  toolCalls: {
    marginBottom: Spacing.sm,
    gap: Spacing.xs,
  },
  timestamp: {
    ...Typography.caption,
    marginTop: Spacing.xs,
    textAlign: 'right',
    opacity: 0.6,
  },
});
