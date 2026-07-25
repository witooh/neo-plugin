package account

type Repository interface {
	Find(id string) (*Account, error)
}

type InMemoryRepository struct {
	accounts map[string]*Account
}

func NewInMemoryRepository(accounts map[string]*Account) *InMemoryRepository {
	return &InMemoryRepository{accounts: accounts}
}

func (r *InMemoryRepository) Find(id string) (*Account, error) {
	acc, ok := r.accounts[id]
	if !ok {
		return nil, ErrNotFound
	}
	return acc, nil
}
