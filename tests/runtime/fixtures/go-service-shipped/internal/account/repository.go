package account

type Repository interface {
	Find(id string) (*Account, error)
	Save(acc *Account) error
}

type InMemoryRepository struct {
	accounts map[string]*Account
}

func NewInMemoryRepository(accounts map[string]*Account) *InMemoryRepository {
	return &InMemoryRepository{accounts: accounts}
}

func (r *InMemoryRepository) Save(acc *Account) error {
	r.accounts[acc.ID] = acc
	return nil
}

func (r *InMemoryRepository) Find(id string) (*Account, error) {
	acc, ok := r.accounts[id]
	if !ok {
		return nil, ErrNotFound
	}
	return acc, nil
}
