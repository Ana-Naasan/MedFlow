export interface paths {
  "/health": {
    get: {
      responses: {
        200: {
          content: {
            "application/json": {
              status: string;
              service: string;
              timestamp: string;
            };
          };
        };
      };
    };
  };
}

export type components = Record<string, never>;