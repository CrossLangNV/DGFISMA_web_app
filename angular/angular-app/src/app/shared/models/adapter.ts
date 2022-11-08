export interface Adapter<T> {
  adapt(item: any): T;
  encode(item: any): T;
}
