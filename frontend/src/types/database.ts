// Database type definitions for Supabase
// This would typically be generated using: supabase gen types typescript

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      users: {
        Row: {
          id: string
          username: string | null
          full_name: string | null
          email: string | null
          robinhood_username: string | null
          settings: Json | null
          is_active: boolean | null
          created_at: string | null
          updated_at: string | null
        }
        Insert: {
          id: string
          username?: string | null
          full_name?: string | null
          email?: string | null
          robinhood_username?: string | null
          settings?: Json | null
          is_active?: boolean | null
          created_at?: string | null
          updated_at?: string | null
        }
        Update: {
          id?: string
          username?: string | null
          full_name?: string | null
          email?: string | null
          robinhood_username?: string | null
          settings?: Json | null
          is_active?: boolean | null
          created_at?: string | null
          updated_at?: string | null
        }
      }
      portfolios: {
        Row: {
          id: string
          user_id: string
          snapshot_date: string | null
          total_value: number | null
          total_return: number | null
          total_return_percent: number | null
          day_return: number | null
          day_return_percent: number | null
          stocks_value: number | null
          options_value: number | null
          cash_value: number | null
          raw_data: Json | null
          created_at: string | null
        }
        Insert: {
          id?: string
          user_id: string
          snapshot_date?: string | null
          total_value?: number | null
          total_return?: number | null
          total_return_percent?: number | null
          day_return?: number | null
          day_return_percent?: number | null
          stocks_value?: number | null
          options_value?: number | null
          cash_value?: number | null
          raw_data?: Json | null
          created_at?: string | null
        }
        Update: {
          id?: string
          user_id?: string
          snapshot_date?: string | null
          total_value?: number | null
          total_return?: number | null
          total_return_percent?: number | null
          day_return?: number | null
          day_return_percent?: number | null
          stocks_value?: number | null
          options_value?: number | null
          cash_value?: number | null
          raw_data?: Json | null
          created_at?: string | null
        }
      }
      stock_positions: {
        Row: {
          id: string
          user_id: string
          symbol: string
          quantity: number
          average_buy_price: number | null
          current_price: number | null
          market_value: number | null
          total_cost: number | null
          total_return: number | null
          total_return_percent: number | null
          raw_data: Json | null
          last_updated: string | null
          created_at: string | null
        }
        Insert: {
          id?: string
          user_id: string
          symbol: string
          quantity: number
          average_buy_price?: number | null
          current_price?: number | null
          market_value?: number | null
          total_cost?: number | null
          total_return?: number | null
          total_return_percent?: number | null
          raw_data?: Json | null
          last_updated?: string | null
          created_at?: string | null
        }
        Update: {
          id?: string
          user_id?: string
          symbol?: string
          quantity?: number
          average_buy_price?: number | null
          current_price?: number | null
          market_value?: number | null
          total_cost?: number | null
          total_return?: number | null
          total_return_percent?: number | null
          raw_data?: Json | null
          last_updated?: string | null
          created_at?: string | null
        }
      }
      options_positions: {
        Row: {
          id: string
          user_id: string
          underlying_symbol: string
          option_type: string
          strike_price: number
          expiration_date: string
          quantity: number
          contracts: number | null
          transaction_side: string
          position_effect: string
          direction: string
          average_price: number | null
          current_price: number | null
          clearing_cost_basis: number | null
          clearing_direction: string | null
          market_value: number | null
          total_cost: number | null
          total_return: number | null
          total_return_percent: number | null
          strategy: string | null
          strategy_type: string | null
          delta: number | null
          gamma: number | null
          theta: number | null
          vega: number | null
          rho: number | null
          implied_volatility: number | null
          days_to_expiry: number | null
          break_even_price: number | null
          max_profit: number | null
          max_loss: number | null
          probability_of_profit: number | null
          opened_at: string | null
          last_updated: string | null
          created_at: string | null
          raw_data: Json | null
        }
        Insert: {
          id?: string
          user_id: string
          underlying_symbol: string
          option_type: string
          strike_price: number
          expiration_date: string
          quantity: number
          contracts?: number | null
          transaction_side: string
          position_effect: string
          direction: string
          average_price?: number | null
          current_price?: number | null
          clearing_cost_basis?: number | null
          clearing_direction?: string | null
          market_value?: number | null
          total_cost?: number | null
          total_return?: number | null
          total_return_percent?: number | null
          strategy?: string | null
          strategy_type?: string | null
          delta?: number | null
          gamma?: number | null
          theta?: number | null
          vega?: number | null
          rho?: number | null
          implied_volatility?: number | null
          days_to_expiry?: number | null
          break_even_price?: number | null
          max_profit?: number | null
          max_loss?: number | null
          probability_of_profit?: number | null
          opened_at?: string | null
          last_updated?: string | null
          created_at?: string | null
          raw_data?: Json | null
        }
        Update: {
          id?: string
          user_id?: string
          underlying_symbol?: string
          option_type?: string
          strike_price?: number
          expiration_date?: string
          quantity?: number
          contracts?: number | null
          transaction_side?: string
          position_effect?: string
          direction?: string
          average_price?: number | null
          current_price?: number | null
          clearing_cost_basis?: number | null
          clearing_direction?: string | null
          market_value?: number | null
          total_cost?: number | null
          total_return?: number | null
          total_return_percent?: number | null
          strategy?: string | null
          strategy_type?: string | null
          delta?: number | null
          gamma?: number | null
          theta?: number | null
          vega?: number | null
          rho?: number | null
          implied_volatility?: number | null
          days_to_expiry?: number | null
          break_even_price?: number | null
          max_profit?: number | null
          max_loss?: number | null
          probability_of_profit?: number | null
          opened_at?: string | null
          last_updated?: string | null
          created_at?: string | null
          raw_data?: Json | null
        }
      }
      options_orders: {
        Row: {
          id: string
          user_id: string
          order_id: string
          underlying_symbol: string
          strategy: string | null
          direction: string
          state: string
          type: string | null
          quantity: number
          price: number | null
          premium: number | null
          processed_premium: number | null
          processed_premium_direction: string | null
          legs_count: number | null
          legs: Json | null
          executions_count: number | null
          executions: Json | null
          option_type: string | null
          strike_price: number | null
          expiration_date: string | null
          transaction_side: string | null
          position_effect: string | null
          total_cost: number | null
          fees: number | null
          net_amount: number | null
          order_created_at: string | null
          order_updated_at: string | null
          filled_at: string | null
          cancelled_at: string | null
          created_at: string | null
          raw_data: Json | null
        }
        Insert: {
          id?: string
          user_id: string
          order_id: string
          underlying_symbol: string
          strategy?: string | null
          direction: string
          state: string
          type?: string | null
          quantity: number
          price?: number | null
          premium?: number | null
          processed_premium?: number | null
          processed_premium_direction?: string | null
          legs_count?: number | null
          legs?: Json | null
          executions_count?: number | null
          executions?: Json | null
          option_type?: string | null
          strike_price?: number | null
          expiration_date?: string | null
          transaction_side?: string | null
          position_effect?: string | null
          total_cost?: number | null
          fees?: number | null
          net_amount?: number | null
          order_created_at?: string | null
          order_updated_at?: string | null
          filled_at?: string | null
          cancelled_at?: string | null
          created_at?: string | null
          raw_data?: Json | null
        }
        Update: {
          id?: string
          user_id?: string
          order_id?: string
          underlying_symbol?: string
          strategy?: string | null
          direction?: string
          state?: string
          type?: string | null
          quantity?: number
          price?: number | null
          premium?: number | null
          processed_premium?: number | null
          processed_premium_direction?: string | null
          legs_count?: number | null
          legs?: Json | null
          executions_count?: number | null
          executions?: Json | null
          option_type?: string | null
          strike_price?: number | null
          expiration_date?: string | null
          transaction_side?: string | null
          position_effect?: string | null
          total_cost?: number | null
          fees?: number | null
          net_amount?: number | null
          order_created_at?: string | null
          order_updated_at?: string | null
          filled_at?: string | null
          cancelled_at?: string | null
          created_at?: string | null
          raw_data?: Json | null
        }
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}