(function () {
  const DB_NAME = "akyl-web-cache";
  const STORE_NAME = "records";
  const DB_VERSION = 1;
  let databasePromise = null;

  function openDatabase() {
    if (!window.indexedDB) return Promise.resolve(null);
    if (databasePromise) return databasePromise;

    databasePromise = new Promise((resolve) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = () => {
        const database = request.result;
        if (!database.objectStoreNames.contains(STORE_NAME)) {
          database.createObjectStore(STORE_NAME, { keyPath: "key" });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => resolve(null);
    });
    return databasePromise;
  }

  async function run(mode, operation) {
    const database = await openDatabase();
    if (!database) return null;
    return new Promise((resolve) => {
      const transaction = database.transaction(STORE_NAME, mode);
      const store = transaction.objectStore(STORE_NAME);
      const request = operation(store);
      request.onsuccess = () => resolve(request.result ?? true);
      request.onerror = () => resolve(null);
    });
  }

  function namespace(userUuid, key) {
    return `${userUuid || "guest"}:${key}`;
  }

  window.AkylStore = {
    scope(userUuid) {
      return {
        async get(key) {
          const record = await run("readonly", (store) => store.get(namespace(userUuid, key)));
          return record ? record.value : null;
        },
        async set(key, value) {
          return run("readwrite", (store) => store.put({
            key: namespace(userUuid, key),
            value,
            updatedAt: Date.now(),
          }));
        },
        async remove(key) {
          return run("readwrite", (store) => store.delete(namespace(userUuid, key)));
        },
      };
    },
  };
})();
