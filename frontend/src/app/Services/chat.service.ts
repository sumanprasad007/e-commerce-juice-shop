/*
 * Copyright (c) 2014-2026 Bjoern Kimminich & the OWASP Juice Shop contributors.
 * SPDX-License-Identifier: MIT
 */

import { Injectable, inject } from '@angular/core'
import { HttpClient } from '@angular/common/http'
import { environment } from '../../environments/environment'

export interface ChatChunk {
  deltaContent?: string
  deltaToolCalls?: ToolCall[]
  finishReason?: string | null
  error?: string
}

export interface ToolCall {
  id: string
  type: string
  function: { name: string, arguments: string }
}

interface AssistantResponse {
  answer: string
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  private readonly http = inject(HttpClient)
  private readonly host = environment.aiAssistantServer + '/chat'

  async * streamMessages (messages: { role: string, content: string }[]): AsyncGenerator<ChatChunk> {
    try {
      const response = await this.http.post<AssistantResponse>(this.host, {
        message: messages.at(-1)?.content ?? ''
      }).toPromise()
      if (response) yield { deltaContent: response.answer }
    } catch {
      yield { error: 'connection_failed' }
    }
  }
}
